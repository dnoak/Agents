from dataclasses import dataclass
import json
import os
from elasticsearch import Elasticsearch, helpers
from utils.ghotsdb import GhostDb
import warnings
import openai

warnings.filterwarnings("ignore")

@dataclass
class ElasticNectarBlog:
    index: str
    hosts: str
    basic_auth: tuple[str, str]
    verify_certs: bool = False

    def __post_init__(self):
        self.es = Elasticsearch(
            hosts=self.hosts,
            basic_auth=self.basic_auth,
            verify_certs=self.verify_certs,
        )

    @property
    def mapping(self):
        return {
            "settings": {
                'index': {
                    'number_of_shards': 3,
                    'number_of_replicas': 2
                },
                "analysis": {
                    "analyzer": {
                        "custom_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},  # ID do artigo
                    "chunk_index": {"type": "integer"},  # Ordem do chunk no artigo
                    "tags": {"type": "keyword"},  # Tags usadas na busca
                    "title": {
                        "type": "text",
                        "analyzer": "custom_analyzer"  # Busca mais eficiente
                    },
                    "text": {
                        "type": "text",
                        "analyzer": "custom_analyzer"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 1536,  # Dimensão dos embeddings
                        "index": True,
                        "similarity": "cosine"  # Similaridade de cosseno
                    },
                    "created_at": {
                        "type": "date",
                        "format": "yyyy-MM-dd HH:mm:ss"
                    }
                }
            }
        }
    
    def delete_index(self):
        delete = input('Type YES to delete index... ')
        if delete == 'YES':
            return self.es.indices.delete(index=self.index)
        print('Index not deleted')
    
    def create_index(self):
        self.es.indices.create(
            index=self.index,
            body=self.mapping
        )
    
    def insert(self, documents: dict | list[dict]):
        if isinstance(documents, list):
            helpers.bulk(client=self.es, actions=documents, index=self.index) 
        else:
            self.es.index(index=self.index, body=documents)        

    def search(
            self, query_text: str, query_vector: list[float], size: int = 10):
        """
        Busca híbrida (BM25 + embeddings), retornando os top N documentos mais relevantes.

        :param query_text: Texto da busca (usado para BM25).
        :param query_vector: Vetor da busca (usado para similaridade com embeddings).
        :param size: Número máximo de documentos retornados.
        :return: Lista de documentos mais relevantes com seus respectivos scores.
        """
        query = {
            "size": size,
            "query": {
                "bool": {
                    "should": [
                        # BM25 com fuzziness
                        { "match": { "title": { "query": query_text, "fuzziness": "AUTO" } } },
                        { "match": { "text": { "query": query_text, "fuzziness": "AUTO" } } },

                        # Busca fonética
                        { "match": { "title_phonetic": query_text } },
                        { "match": { "text_phonetic": query_text } },

                        # Similaridade de embeddings (cosine similarity)
                        { "script_score": {
                            "query": { "match_all": {} },  
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                "params": { "query_vector": query_vector }
                            }
                        }}
                    ],
                    "minimum_should_match": 1  # Garante que pelo menos um critério seja atendido
                }
            },
            "sort": [
                "_score"  # Ordena pelo score final (BM25 + embeddings)
            ]
        }

        response = self.es.search(index=self.index, body=query)

        # Retornar os documentos junto com o _score
        return [
            {**hit["_source"], "_score": hit["_score"]}
            for hit in response["hits"]["hits"]
        ]
    
    def format_search_result(self, results: list[dict]) -> str:
        formatted = []
        for index, result in enumerate(results):
            formatted.append(f"Resultado ({index + 1}):\n")
            formatted.append(f"Título: {result['title']}\n")
            formatted.append(f"Tags: {', '.join(result['tags'])}\n")
            formatted.append(f"Index do fragmento: {result['chunk_index']}\n")
            formatted.append(f"Fragmento do texto: {result['text']}\n")
            formatted.append('\n')
        return ''.join(formatted)


def gen_ghost_db():
    ghost_db = GhostDb(
        path='data/nectar/blog-da-nectarcrm-i-conteudo-de-valor-para-equipes-de-vendas.ghost.2025-02-10-16-28-49.json',
        chunk_size=1024,
        chunk_overlap=int(0.25 * 1024),
        samples=None
    )
    ghost_db.generate_embeddings(
        openai_api_key=os.environ['OPENAI_API_KEY'],
        max_request_size=2048
    )
    ghost_db.save_json(
        path='data/nectar/elastic.json'
    )

def recreate_index(elastic_nectar: ElasticNectarBlog):
    elastic_nectar.delete_index()
    elastic_nectar.create_index()
    with open('data/nectar/elastic.json', 'r', encoding='utf-8') as file:
        articles = json.load(file)
    elastic_nectar.insert(articles)

if __name__ == '__main__':

    nectar_blog = ElasticNectarBlog(
        index='nectar_blog',
        hosts=os.environ['ELASTIC_HOST'],
        basic_auth=(os.environ['ELASTIC_USER'], os.environ['ELASTIC_PASSWORD']),
        verify_certs=False,
    )

    # gen_ghost_db()
    # recreate_index(nectar_blog)

    while True:
        print('\n\n\n')
        text = input('Type a search text: ')
        vector = openai.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        ).data[0].embedding

        res = nectar_blog.search(query_text=text, query_vector=vector, size=10)

        # for r in res:
        #     print(f"✅ score: {r['_score']}")
        #     print(f"🔴 index: {r['chunk_index']}")
        #     print(f"🟡 title: {r['title']}")
        #     print(f"🟣 tags: {r['tags']}")
        #     print(f"🟢 text: {r['text']}")
        #     print()

        print(nectar_blog.format_search_result(res))

    # [print(json.dumps(shark, indent=2, ensure_ascii=False)) for shark in s]