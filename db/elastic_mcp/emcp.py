from dataclasses import dataclass
import json
import os
import typing
from elasticsearch import Elasticsearch, helpers
from pydantic import Field
from pydantic.fields import FieldInfo
import re
from models.agent import Tool
from rich import print

@dataclass
class ElasticTools:
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
                "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            },
            "analysis": {
                "analyzer": {
                    "custom_pt_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "asciifolding",
                            "stop_ptbr",
                            "stemmer_ptbr"
                        ]
                    }
                },
                "filter": {
                    "stop_ptbr": {
                        "type": "stop",
                        "stopwords": "_portuguese_" 
                    },
                    "stemmer_ptbr": {
                        "type": "stemmer",
                        "language": "brazilian"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "id": {
                    "type": "keyword"
                },
                "name": {
                    "type": "text",
                    "analyzer": "custom_pt_analyzer"
                },
                "description": {
                    "type": "text",
                    "analyzer": "custom_pt_analyzer"
                },
                "description_embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine"
                },
                "docs": {
                    "type": "text",
                    "analyzer": "custom_pt_analyzer"
                },
                "docs_embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine"
                },
                "keywords": {
                    "type": "text",
                    "analyzer": "custom_pt_analyzer"
                },
                "keywords_embedding": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine"
                },
                "returns": {
                    "type": "text",
                    "analyzer": "custom_pt_analyzer"
                }
            }
        }
    }

    def search(
            self, text: str, embedding: list[float], k: int = 10):
        query = {
            "size": 5,
            "query": {
                "bool": {
                "should": [
                    {
                    "multi_match": {
                        "query": text,
                        "fields": [
                            "name",
                            "description",
                            "docs",
                            "returns",
                            "keywords"
                        ],
                        "fuzziness": "AUTO",
                        "analyzer": "custom_analyzer"
                    }
                },
                {
                    "script_score": {
                        "query": { "match_all": {} },
                        "script": {
                        "source": """
                            cosineSimilarity(params.query_vector, 'name_embedding') + 
                            cosineSimilarity(params.query_vector, 'description_embedding') + 
                            cosineSimilarity(params.query_vector, 'docs_embedding') + 
                            cosineSimilarity(params.query_vector, 'returns_embedding') + 
                            cosineSimilarity(params.query_vector, 'keywords_embedding')
                        """,
                        "params": {
                            "query_vector": embedding
                        }
                    }
                }
                }
                ],
                "minimum_should_match": 1
                }
            }
        }
        response = self.es.search(index=self.index, body=query)
        return [
            {**hit["_source"], "_score": hit["_score"]}
            for hit in response["hits"]["hits"]
        ]
    
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

    def insert(self, documents: type[Tool]):
        print(type)
        # if isinstance(documents, list):
        #     helpers.bulk(client=self.es, actions=documents, index=self.index) 
        # else:
        #     self.es.index(index=self.index, body=documents)
    
    @staticmethod
    def generate_search_query(tool_document: dict) -> tuple[str, list[float]]:
        formatted = ''
        for field_name, field_value in tool_document.items():
            if field_value is None:
                continue
            formatted += f'{field_name}: '
            if isinstance(field_value, str):
                formatted += f'{field_value}\n'
            elif isinstance(field_value, list):
                formatted += '; '.join(field_value) + '\n'
            else:
                raise TypeError(f'Usuported type {field_name}: {type(field_value)}')
        return formatted, [i for i in range(768)]

@dataclass
class ToolElasticDocumentGenerator:
    tool: type[Tool]

    def __post_init__(self):
        self._typing_to_json: dict[str, str] = {
            'None': 'null',
        }
    
    def _format_field_type(self, field_value: FieldInfo | type) -> str:
        if isinstance(field_value, type):
            return field_value.__name__
        if isinstance(field_value.annotation, type):
            return field_value.annotation.__name__
        formatted = re.sub(r"\b[\w\d_]+\.", "", str(field_value.annotation))
        for python_type, json_type in self._typing_to_json.items():
            formatted = formatted.replace(python_type, json_type)
        return formatted
    
    def _tool_return_type(self, tool: type[Tool]) -> str:
        return_annotation = typing.get_type_hints(getattr(tool, 'tool'))['return']
        return self._format_field_type(return_annotation)
    
    def _tool_docs(self) -> list[str]:
        args = []
        for field_name, field_value in self.tool.model_fields.items():
            arg = f'{field_name}: {self._format_field_type(field_value)} - {field_value.description}'
            args.append(arg)
        return args

    def generate(self) -> dict:
        assert self.tool.__doc__ is not None, f'tool {self.tool.__name__} has no documentation'
        return {
            'name': self.tool.__name__,
            'description': self.tool.__doc__.strip(),
            'docs': self._tool_docs(),
            # 'keywords': self.tool.__shared__,
            'returns': self._tool_return_type(self.tool),
        }

if __name__ == '__main__':
    import random
    from agents.smart_home.security import MotionSensorStatus
    
    # print(MotionSensorStatus(
    #     location='sala',
    #     sensor_id=2,
    #     check_interval_seconds=3,
    # ))
    tool_doc = ToolElasticDocumentGenerator(MotionSensorStatus)
    # print(tool_doc.generate())

    # print(ElasticTools.generate_search_query(tool_doc.generate()))