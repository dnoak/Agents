from dataclasses import dataclass
import more_itertools as mit
import os
from pathlib import Path
import random
from typing import Optional
from langchain.text_splitter import NLTKTextSplitter
import json
# from matplotlib import pyplot as plt
import openai
from tqdm import tqdm

@dataclass
class GhostDb:
    path: str
    chunk_size: int
    chunk_overlap: int
    samples: Optional[int]

    def __post_init__(self):
        with open(self.path, 'r', encoding='utf-8') as f:
            self.db: dict = json.load(f)['db'][0]
        self.tags: dict[str, str] = self._get_tags()
        self.posts_chunks: list[dict] = self._get_posts_chunks(
            chunk_size=self.chunk_size, 
            chunk_overlap=self.chunk_overlap
        )

    def _get_tags(self) -> dict[str, str]:
        return {tag['id']: tag['name'] for tag in self.db['data']['tags']}
    
    def _get_posts_chunks(self, chunk_size, chunk_overlap: float):
        posts = [post for post in self.db['data']['posts']]
        #if self.samples is not None:
        #posts = random.sample(posts, self.samples)
        tags = [tag for tag in self.db['data']['posts_tags']]
        tags += (len(posts) - len(tags)) * [None]
        assert len(posts) <= len(tags)
        	
        tags_by_post_id = {post['id']: [] for post in posts}
        for tag in tags:
            if tag is None:
                continue
            # if tag['post_id'] not in tags_by_post_id:
            #     tags_by_post_id[tag['post_id']] = []
            tags_by_post_id[tag['post_id']].append(self.tags[tag['tag_id']])

        chunked_posts = []
        random.shuffle(posts)
        for post in posts[:self.samples]:
            if post['plaintext'] is None:
                continue
            text_splitter = NLTKTextSplitter(
                separator="\n",
                language='portuguese',
                chunk_size=chunk_size, 
                chunk_overlap=chunk_overlap, 
            )
            chunked_post = text_splitter.split_text(post['plaintext'])
            for chunk_index, chunk in enumerate(chunked_post):
                chunked_posts.append({
                    'id': post['id'],
                    'chunk_index': chunk_index,
                    'tags': tags_by_post_id[post['id']],
                    'title': post['title'],
                    'text': chunk.replace('\n', ' '),
                    'embedding': None,
                    'created_at': post['created_at'],
                })
        return chunked_posts
    
    def generate_embeddings(self, openai_api_key: str, max_request_size=2048):
        openai.api_key = openai_api_key

        for chunk in tqdm(mit.chunked(self.posts_chunks, max_request_size)):
            texts = [post['text'] for post in chunk]
            response = openai.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            for post, embedding in zip(chunk, response.data):
                post['embedding'] = embedding.embedding

    def save_json(self, path: str):
        os.makedirs(Path(path).parent, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.posts_chunks, f, indent=4, ensure_ascii=False)

    def plot_metrics(self):
        # fig, ax = plt.subplots(figsize=(10, 7))
        # words_list = []
        # for post in self.posts_chunks:
        #     words_list.append(sum(len(p.split()) for p in post['text']))

        # ax.hist(words_list, bins=20)
        # ax.set_xlabel('Tamanho do texto')
        # ax.set_ylabel('Número de posts')
        # ax.text()
        # plt.show()
        ...

