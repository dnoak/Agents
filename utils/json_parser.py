import json

def extract_json(s: str) -> dict:
    s = s[next(idx for idx, c in enumerate(s) if c in "{["):]
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        try:
            return json.loads(s[:e.pos])
        except:
            return extract_json(s[e.pos:])

if __name__ == "__main__":
    # 1. Lixo antes do JSON
    entrada = "texto irrelevante {\"key\": \"value\"}"
    esperado = {"key": "value"}
    print("Teste 1:", extract_json(entrada) == esperado)

    # 2. Lixo antes e depois do JSON (array com objetos)
    entrada = "algum lixo antes [{\"a\": 1}, 2, 3] e lixo depois"
    esperado = [{"a": 1}, 2, 3]
    print("Teste 2:", extract_json(entrada) == esperado)

    # 3. JSON com lixo imediatamente após o objeto
    entrada = "inicio {\"a\": 1}garbage"
    esperado = {"a": 1}
    print("Teste 3:", extract_json(entrada) == esperado)

    # 4. JSON sem nenhum lixo (formato ideal)
    entrada = "{\"a\":1}"
    esperado = {"a": 1}
    print("Teste 4:", extract_json(entrada) == esperado)

    # 5. Múltiplos objetos JSON na mesma string: espera capturar o primeiro objeto válido
    entrada = "junk {\"a\":1} more text {\"b\":2}"
    esperado = {"a": 1}
    print("Teste 5:", extract_json(entrada) == esperado)

    # 6. JSON aninhado com array e objeto, com lixo no final
    entrada = "random text [{\"a\": [1, 2, 3]}, {\"b\": {\"c\": \"d\"}}] trailing garbage"
    esperado = [{"a": [1, 2, 3]}, {"b": {"c": "d"}}]
    print("Teste 6:", extract_json(entrada) == esperado)

    # 7. Caso sem nenhum JSON válido (deve lançar erro)
    entrada = "este texto não contém nenhum JSON válido"
    try:
        resultado = extract_json(entrada)
        sucesso = False  # Se chegar aqui, o teste falhou
    except StopIteration:
        sucesso = True  # Esperado, pois não há caractere de abertura de JSON
    print("Teste 7:", sucesso)

    # 8. JSON incompleto (teste desafiador)
    entrada = "antes {\"incompleto\": true"  # Falta o fechamento }
    try:
        resultado = extract_json(entrada)
        # Se o corte ocorrer na posição correta, pode dar erro ou retornar um JSON válido incompleto.
        # Aqui, apenas exibimos o resultado para análise.
        print("Teste 8: Resultado:", resultado)
    except StopIteration:
        print("Teste 8: True (sem json válido)")

    entrada = """
    [message 3 - assistant]:
    ```json
    {
        "__reasoning__": "Primeiro, calculo a expressão dentro dos parênteses: 523.421 * 2982.18 = 1564730.57. Em seguida, adiciono 237.291: 1564730.57 + 237.291 = 1564967.861. Agora divido por 1204.1927: 1564967.861 / 1204.1927 = 1301.703. Finalmente, subtraio 1437.583 de 1301.703: 1301.703 - 1437.583 = -135.88. ",
        "tool_task": {
            "status": "pending",
            "steps": [],
            "tools_query": ""
        },
        "result": -135.88
    }
    ```
    [lixo]
    """
    esperado = {
        "__reasoning__": "Primeiro, calculo a expressão dentro dos parênteses: 523.421 * 2982.18 = 1564730.57. Em seguida, adiciono 237.291: 1564730.57 + 237.291 = 1564967.861. Agora divido por 1204.1927: 1564967.861 / 1204.1927 = 1301.703. Finalmente, subtraio 1437.583 de 1301.703: 1301.703 - 1437.583 = -135.88. ",
        "tool_task": {
            "status": "pending",
            "steps": [],
            "tools_query": ""
        },
        "result": -135.88
    }
    print("Teste 9:", extract_json(entrada) == esperado)

    entrada = """{"nome": "John"} {"idade": 30}"""
    esperado = {"nome": "John"}
    print("Teste 10:", extract_json(entrada) == esperado)