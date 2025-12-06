
import ast
from dataclasses import dataclass, field
import asyncio
import json
from typing import Literal, Optional, Type, ClassVar
import typing
from termcolor import colored
from src.input_queue import InputQueues, ChatTriggers
from models.agent import AgentOutput, Processor, Replicator, Classifier
from src.message import Message, Messages, MessagesMerger
from src.llm import LLM
from PIL import Image
from io import BytesIO
import uuid
import numpy as np
import cv2
import graphviz
from rich import print


@dataclass(kw_only=True)
class Agent:
    name: str
    role: Literal['user', 'user:linked', 'assistant', 'system']
    output_schema: type[AgentOutput]
    llm: Optional[LLM] = None
    processor: Optional[Processor] = None
    num_workers: int
    graph_attr: ClassVar[dict[str, str]] = {
        'size': '500,500',
        'bgcolor': '#353B41',
    }
    debug: bool = False

    def __post_init__(self):
        if self.llm is None and self.processor is None:
            raise Exception("You must set either `llm` or `processor` for the agent.")
        self.id = str(uuid.uuid4())
        # self.inputs_queue: InputQueues = InputQueues(agent=self, triggers=ChatTriggers())
        self.started: bool = False
        self.output_nodes: list[Agent] = []
        self.input_nodes: list[Agent] = []
        self.required_input_nodes_ids: set[str] = set()
        Agent.alocker: asyncio.Lock = asyncio.Lock()
        Agent.animate: bool = False
        if not hasattr(Agent, 'metadata'):
            Agent.metadata = {}
        if not hasattr(Agent, 'graph'):
            Agent.graph = graphviz.Digraph(graph_attr=self.graph_attr) # type: ignore
        Agent.graph.node(
            name=self.name,
            label=self.output_schema.node_label(self), 
            **self.output_schema.node_attributes(),
        )
    
    def _init_workers(self):
        if not self.started:
            self.started = True
            for _ in range(self.num_workers):
                asyncio.create_task(self._start_loop())

    async def _start_loop(self):        
        while True:
            await self._start()
    
    async def _start(self) -> dict:
        messages = await self.inputs_queue.get()

        if Agent.animate:
            Agent.graph.node(name=self.name, label=self.output_schema.node_label(self, running=True))
        
        llm = await self._async_llm(MessagesMerger(
            id=messages[0].id,
            messages=messages,
            source=self,
        ).merge())

        processed = self._sync_processor(messages, llm)
        if Agent.animate:
            Agent.graph.node(name=self.name, label=self.output_schema.node_label(self)) 
        return await self._node_choice(messages, processed)
    
    def _execute_tool_task(self, query: str) -> str:
        try:
            tree = ast.parse(query, mode='eval')
            if not isinstance(tree.body, ast.Call):
                return 'ExpressionError("expression is not a valid function call")'
            if not isinstance(tree.body.func, ast.Name):
                return 'TypeError("function name is not a valid identifier")'
            func_name = tree.body.func.id
            if func_name not in  self.llm.instructions.validated_tools:
                return f"NotFoundError(function '{func_name}' not registered in [Tools])"
            args = [
                self._execute_tool_task(ast.unparse(arg)) if isinstance(arg, ast.Call) 
                else eval(compile(ast.Expression(arg), "<string>", "eval")) 
                for arg in tree.body.args
            ]
            instance =  self.llm.instructions.validated_tools[func_name](**dict(zip(["a", "b"], args)))
            return instance.tool()
        except Exception as e:
            return 'Exception:\n' + str(e)
    
    async def _async_llm(self, messages: Messages) -> dict:
        if not self.llm:
            return {}
        messages.instructions = self.llm.instructions.content
        tool_usage_id = str(uuid.uuid4())
        while True:
            llm_result = await self.llm.acomplete(
                id=messages.id,
                messages=messages,
                metadata=Agent.metadata,
                roles_filter={
                    'user': 'all', 
                    'assistant': 
                    'all', 'system': 
                    'all', 
                    'tool:step': tool_usage_id,
                    'tool:result': 'all',
                },
            )

            if not self.llm.instructions.tools:
                return llm_result

            if llm_result['_task_completion_status'] in ['success', 'failed']:
                if messages.last.role == 'tool:step':
                    messages.data.append(Message(
                        id=tool_usage_id,
                        content={'tool_usage': llm_result, 'query_result': messages.last.content['query_result']},
                        role='tool:result',
                    ))
                return llm_result
            
            messages.data.append(Message(
                id=tool_usage_id,
                content={
                    'tool_usage': llm_result, 
                    'query_result': f"{llm_result['_tool_query']} = {self._execute_tool_task(llm_result['_tool_query'])}"
                },
                role='tool:step',
            ))

    def _sync_processor(self, messages: list[Messages], llm: dict) -> dict:
        if self.processor:
            processed = self.processor.process(agent=self, messages=messages, llm=llm)
            return processed if processed is not None else llm
        return llm

    async def _node_choice(self, messages: list[Messages], result: dict) -> dict:
        if not self.output_nodes:
            return result
        
        history = MessagesMerger(
            id=messages[0].id,
            messages=messages,
            source=self,
        ).merge().history

        # if self.output_schema.connection_type() == Replicator.connection_type():
        #     for output_node in self.output_nodes:
        #         output_node.run(Messages(
        #             id=messages[0].id,
        #             data=history + [Message(content=result, role=self.role)],
        #             source=self
        #         ))

        if self.output_schema.connection_type() == Replicator.connection_type():
            for output_node in self.output_nodes:
                # output_node.run(
                #     message=Message(id=str(uuid.uuid4()), content=result, role=self.role),
                #     chat_id=messages[0].id,
                #     source=self
                
                # )
                output_node.run(
                    messages=Messages(
                        id=messages[0].id,
                        data=[Message(id=str(uuid.uuid4()), content=result, role=self.role)],
                        source=self
                    )
                )

        elif self.output_schema.connection_type() == Classifier.connection_type():
            selected_nodes = [k for k, v in result.items() if v is True]
            valid_result = False
            for output_node in self.output_nodes:
                if output_node.name in selected_nodes:
                    # output_node.run(
                    #     message=Message(id=str(uuid.uuid4()), content=result, role=self.role),
                    #     chat_id=messages[0].id,
                    #     source=self
                    # )
                    output_node.run(
                        messages=Messages(
                            id=messages[0].id,
                            data=[Message(id=str(uuid.uuid4()), content=result, role=self.role)],
                            source=self
                        )
                    )
                    valid_result = True
            if not valid_result:
                raise Exception(colored(
                    f'\n❌ ❌ ❌ No connection node(s) found in <Classifier> output for agent `{self.name}`\n'
                    f'  available nodes: {[n.name for n in self.output_nodes]}\n',
                    color='red', attrs=['bold']
                ))
        return result

    def update_metadata(self, key: str, value: dict):
        if key not in Agent.metadata:
            Agent.metadata[key] = []
        Agent.metadata[key].append(value)

    async def aupdate_metadata(self, key: str, value: dict):
        async with Agent.alocker:
            self.update_metadata(key, value)

    def plot(self, animate: bool = False):
        if not animate:
            return Image.open(BytesIO(Agent.graph.pipe(format='png'))).show()

        def update_graph():
            while True:
                data = Agent.graph.pipe(format='jpeg', engine='dot') # 0.2 ~ 0.3s por frame
                img_np = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
                cv2.namedWindow("Graph Animation", cv2.WINDOW_AUTOSIZE)
                cv2.imshow("Graph Animation", img_np)
                if cv2.waitKey(500) & 0xFF == 27:
                    break
            cv2.destroyAllWindows()
        Agent.animate = True
        update_graph()

    def connect(self, agent: 'Agent', required: bool = True):
        self.output_nodes.append(agent)
        agent.input_nodes.append(self)
        if required:
            agent.required_input_nodes_ids.add(self.id)

        attributes = self.output_schema.edge_attributes()
        if not required:
            attributes['style'] = 'dashed'
            attributes['arrowhead'] = 'odot'
        Agent.graph.edge(
            tail_name=self.name,
            head_name=agent.name, 
            **attributes
        )
    
    def run(self, messages: Messages):
        self._init_workers()
        self.inputs_queue.put(messages)
