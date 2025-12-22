import time
import datetime
import asyncio

async def a():
    return ['a']

async def main():
    x = [a()]
    y = ['y']

    res = sum(await asyncio.gather(*x), [])
    # print(res)
    return res or y

print(asyncio.run(main()))