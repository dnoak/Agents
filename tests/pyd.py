from pydantic import BaseModel

class NodeOutputSchema(BaseModel):
    a: str
    b: int
    c: dict[str, int]

class NodeOutput(BaseModel):
    output_schema: NodeOutputSchema

node = NodeOutput(output_schema=NodeOutputSchema(a='a', b=1, c={'a': 1}))

for k, v in node.output_schema.annotations().items():
    print(f'{k}: {v}')