from dataclasses import dataclass, field
import time
from typing import Literal, Optional
import json
from typing import TYPE_CHECKING
from datetime import datetime
import uuid
from rich import print
if TYPE_CHECKING:
    from src.agent import Agent
    from src.instructions import LlmInstructions

@dataclass(kw_only=True)
class Message:
    id: str
    content: dict
    role: Literal['user', 'user:linked', 'assistant', 'tool:step', 'tool:result', 'system'] 
    timestamp: float = field(default_factory=lambda: time.time())

    def format(self) -> dict:
        content = self.content
        if len(self.content.keys()) == 1:
            content = self.content[list(self.content.keys())[0]]
            if isinstance(content, str):
                return {'content': content, 'role': self.role}
        return {'content': json.dumps(content, indent=4, ensure_ascii=False), 'role': self.role}
        # formatted = []
        # for index, message in enumerate(self.content):
        #     formatted.append(f'[message {index} - {message.role}]:\n')
        #     keys = list(message.content.keys())
        #     if len(keys) == 1:
        #         formatted.append(f"{keys[0]}:\n{str(message.content[keys[0]])}" + '\n\n')
        #     else:
        #         formatted.append(json.dumps(message.content, indent=4, ensure_ascii=False) + '\n\n')
        # return ''.join(formatted).strip('\n')
        #else:
            #dumped_content = json.dumps(self.content, indent=4, ensure_ascii=False)

# @dataclass
# class RoleFilter:
#     role: Literal['user', 'user:linked', 'assistant', 'assistant:tool', 'system']


@dataclass
class Messages:
    id: str
    data: list[Message]
    # history: list['Message']
    # role: Literal['user', 'user:linked', 'assistant', 'system']
    source: Optional['Agent']

    def __post_init__(self):
        self.start_index = 0

    def _filter_roles(
            self,
            data: list[Message],
            roles_filter: dict[str, str] | Literal['basic', 'debug'] 
        ) -> list[Message]:
        if roles_filter == 'debug':
            return data
        if roles_filter == 'basic':
            return list(filter(lambda m: m.role in ['user', 'assistant', 'system'], data))
        filtered = []
        for d in data:
            if d.role not in roles_filter.keys():
                continue
            if roles_filter[d.role] == 'all':
                filtered.append(d)
                continue
            if roles_filter[d.role] == d.id:
                filtered.append(d)
                continue
        return filtered
    
    def append(self, messages: 'Messages'):
        assert self.id == messages.id
        assert self.source == messages.source
        self.data += messages.history

    def to_llm(self, roles_filter: dict[str, str] | Literal['basic', 'debug']) -> list[dict]:
        role_mapping = {
            'user': 'user',
            'user:linked': 'user',
            'assistant': 'assistant',
            'tool:step': 'user',
            'tool:result': 'user',
            'system': 'system',
        }
        formatted = []
        for m in self._filter_roles(self.data, roles_filter):
            # if roles_filter != 'all' and m.role not in roles_filter:
            #     continue
            content = m.content
            if len(m.content.keys()) == 1:
                content = m.content[list(m.content.keys())[0]]
                if isinstance(content, str):
                    content = {'content': content, 'role': role_mapping[m.role]}
            else:
                content = {
                    'content': json.dumps(content, indent=4, ensure_ascii=False), 
                    'role': role_mapping[m.role]
                }
            formatted.append(content)
        return formatted

    @property
    def instructions(self) -> Message:
        return self.data[0]
    
    @instructions.setter
    def instructions(self, _instructions: str):
        self.data.insert(0, Message(
            id=str(uuid.uuid4()),
            content={'sys': _instructions}, 
            role='system')
        )
        self.start_index = 1

    @property
    def history(self) -> list[Message]:
        # print(self.start_index)
        # print(len(self.data))
        return self.data[self.start_index:]
    
    @property
    def last(self) -> Message:
        return self.data[-1]


@dataclass
class MessagesMerger:
    id: str
    messages: list[Messages]
    source: Optional['Agent']

    def merge(self) -> Messages:
        if len(self.messages) == 1:
            return self.messages[-1]
        
        # history = self.messages[-1].history[:-1]
        # merged = Message(
        #     id=str(uuid.uuid4()),
        #     content={'inputs': [m.last.content for m in self.messages]},
        #     role=self.messages[0].last.role,
        # )
        # return Messages(
        #     id=self.id,
        #     data=history + [merged],
        #     source=self.source,
        # )
        messages_list: list[Message] = self.messages[0].data
        # messages_sources = [
        #     m.source.name if m.source is not None else 'None' 
        #     for m in self.messages
        # ]

        for m in self.messages[1:]:
            for h in m.history:
                messages_list.append(h)
        
        return Messages(
            id=self.id,
            data=messages_list,
            source=self.source,
        )
            
                

if __name__ == '__main__':
    import json

    a = Messages(
        id='a1',
        data=[
            Message(id=str(uuid.uuid4()), content={'a': 1}, role='user'),
            Message(id=str(uuid.uuid4()), content={'a': 2}, role='assistant'),
            Message(id=str(uuid.uuid4()), content={'a': 3,'b': 3}, role='user'),
        ], 
        source=None,
    )
    a.instructions = 'Instruções do agente A'

    b = Messages(
        id='b1',
        data=[
            Message(id=str(uuid.uuid4()), content={'b': 4}, role='user'),
            Message(id=str(uuid.uuid4()), content={'b': 5}, role='user'),
            Message(id=str(uuid.uuid4()), content={'b': 6}, role='assistant'),
        ], 
        source=None,
    )
    b.instructions = 'Instruções do agente B'

    merged = (MessagesMerger(
        id='merged',
        messages=[a, b],
        source=None,
    ).merge())
    # print(a.instructions)
    # print(merged)
    # print(json.dumps(merged.last.content, indent=4, ensure_ascii=False))
    
    print(merged)


