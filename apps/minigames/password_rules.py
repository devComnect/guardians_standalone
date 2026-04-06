import random
import re

PASSWORD_RULES_DB = {
    # FÁCIL
    101: {"id": 101, "diff": "easy",   "desc": "Mínimo de 8 caracteres.",                              "regex": r"^.{8,}$"},
    102: {"id": 102, "diff": "easy",   "desc": "Pelo menos um número.",                                "regex": r"\d"},
    103: {"id": 103, "diff": "easy",   "desc": "Pelo menos uma letra maiúscula.",                      "regex": r"[A-Z]"},
    104: {"id": 104, "diff": "easy",   "desc": "Pelo menos um caractere especial (!@#$).",             "regex": r"[!@#$%^&*(),.?\":{}|<>]"},
    105: {"id": 105, "diff": "easy",   "desc": "Pelo menos duas letras minúsculas.",                   "regex": r"(?:[a-z].*){2}"},
    106: {"id": 106, "diff": "easy",   "desc": "Deve começar com uma letra.",                          "regex": r"^[a-zA-Z]"},
    107: {"id": 107, "diff": "easy",   "desc": "Deve conter um hífen (-) ou underline (_).",           "regex": r"[-_]"},
    109: {"id": 109, "diff": "easy",   "desc": "Pelo menos dois números.",                             "regex": r"(?:\d.*){2}"},
    # MÉDIO
    201: {"id": 201, "diff": "medium", "desc": "Deve conter o ano atual (2025).",                      "regex": r"2025"},
    202: {"id": 202, "diff": "medium", "desc": "Deve começar com 'CMD' ou 'ROOT'.",                    "regex": r"^(CMD|ROOT)"},
    203: {"id": 203, "diff": "medium", "desc": "Deve terminar com três números.",                      "regex": r"\d{3}$"},
    204: {"id": 204, "diff": "medium", "desc": "Não pode conter espaços.",                             "regex": r"^[^ ]*$"},
    205: {"id": 205, "diff": "medium", "desc": "Deve conter uma extensão de script (.PY, .SH, .BAT).", "regex": r"\.(PY|SH|BAT)"},
    206: {"id": 206, "diff": "medium", "desc": "Deve conter 'ADMIN' ou 'USER'.",                       "regex": r"(ADMIN|USER)"},
    207: {"id": 207, "diff": "medium", "desc": "Deve conter o operador matemático '+' ou '='.",        "regex": r"[+=]"},
    209: {"id": 209, "diff": "medium", "desc": "Deve conter três caracteres repetidos em sequência.",  "regex": r"(.)\1\1"},
    210: {"id": 210, "diff": "medium", "desc": "Deve conter exatamente 22 caracteres.",                "regex": r"^.{22}$"},
    # DIFÍCIL
    301: {"id": 301, "diff": "hard",   "desc": "Deve conter um protocolo (HTTP, FTP, SSH, TELNET).",   "regex": r"(HTTP|FTP|SSH|TELNET)"},
    302: {"id": 302, "diff": "hard",   "desc": "Deve conter 'SUDO' em maiúsculas.",                    "regex": r"SUDO"},
    303: {"id": 303, "diff": "hard",   "desc": "Deve conter um numeral romano (I, V, X, L, C).",       "regex": r"[IVXLC]"},
    304: {"id": 304, "diff": "hard",   "desc": "Deve conter uma porta comum (80, 443, 21, 22).",       "regex": r"(80|443|21|22)"},
    305: {"id": 305, "diff": "hard",   "desc": "Deve conter um comando SQL (SELECT, DROP, INSERT).",   "regex": r"(SELECT|DROP|INSERT)"},
    306: {"id": 306, "diff": "hard",   "desc": "Deve conter um formato de email básico (@dominio).",   "regex": r"@\w+\."},
    307: {"id": 307, "diff": "hard",   "desc": "Deve conter 'TRUE' ou 'FALSE'.",                       "regex": r"(TRUE|FALSE)"},
    308: {"id": 308, "diff": "hard",   "desc": "Deve conter um comando Linux (LS, CD, MKDIR, RM).",    "regex": r"(LS|CD|MKDIR|RM)"},
    # INSANO
    401: {"id": 401, "diff": "insane", "desc": "Formato de IP (Ex: 192.168.1.1).",                     "regex": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"},
    402: {"id": 402, "diff": "insane", "desc": "Código Hexadecimal de cor (Ex: #FFFFFF).",             "regex": r"#[0-9A-Fa-f]{6}"},
    404: {"id": 404, "diff": "insane", "desc": "Deve conter uma tag HTML (Ex: <DIV>, <BR>).",          "regex": r"<[A-Z]+>"},
    405: {"id": 405, "diff": "insane", "desc": "Deve conter formato de versão (vX.X.X).",              "regex": r"v\d+\.\d+\.\d+"},
    406: {"id": 406, "diff": "insane", "desc": "Porta lógica (AND, OR, XOR, NOT).",                   "regex": r"\b(AND|OR|XOR|NOT)\b"},
    407: {"id": 407, "diff": "insane", "desc": "Formato de moeda ($99.99).",                           "regex": r"\$\d+\.\d{2}"},
    408: {"id": 408, "diff": "insane", "desc": "NÃO pode conter as vogais A ou I.",                 "regex": r"^[^AIai]*$"},
    # DINÂMICAS (math)
    500: {"id": 500, "diff": "medium", "template": "A soma de todos os números deve ser {}.", "js_type": "sum"},
    501: {"id": 501, "diff": "hard",   "template": "O primeiro número menos o último deve ser {}.", "js_type": "sub_first_last"},
    502: {"id": 502, "diff": "hard",   "template": "O último número menos o primeiro deve ser {}.", "js_type": "sub_last_first"},
}


def generate_rules_sequence(config):
    selected = []

    math_ids = [k for k in PASSWORD_RULES_DB if k >= 500]
    if math_ids and config.rules_count_math > 0:
        for _ in range(config.rules_count_math):
            mid = random.choice(math_ids)
            val = random.randint(15, 50) if mid == 500 else random.randint(1, 8)
            selected.append(f"{mid}:{val}")

    by_diff = {'easy': [], 'medium': [], 'hard': [], 'insane': []}
    for k, v in PASSWORD_RULES_DB.items():
        if k < 500:
            by_diff[v['diff']].append(str(k))

    def sample(pool, n):
        return random.sample(pool, min(len(pool), n))

    selected += sample(by_diff['easy'],   config.rules_count_easy)
    selected += sample(by_diff['medium'], config.rules_count_medium)
    selected += sample(by_diff['hard'],   config.rules_count_hard)
    selected += sample(by_diff['insane'], config.rules_count_insane)

    random.shuffle(selected)
    return selected


def get_rules_details(rules_ids):
    result = []
    for item in rules_ids:
        if ':' in str(item):
            rid, val = str(item).split(':')
            rid, val = int(rid), int(val)
            base = PASSWORD_RULES_DB.get(rid, {}).copy()
            base['desc']   = base['template'].format(val)
            base['js_val'] = val
            base['regex']  = ''
            result.append(base)
        else:
            rule = PASSWORD_RULES_DB.get(int(item))
            if rule:
                result.append(rule)
    return result


def validate_password(password, rules_ids):
    digits = [int(d) for d in password if d.isdigit()]
    failed = []

    for item in rules_ids:
        rid, val = (int(x) for x in str(item).split(':')) if ':' in str(item) else (int(item), 0)
        rule = PASSWORD_RULES_DB.get(rid)
        if not rule:
            continue

        if rid >= 500:
            passed = False
            if digits:
                if rid == 500:
                    passed = sum(digits) == val
                elif rid == 501 and len(digits) >= 2:
                    passed = digits[0] - digits[-1] == val
                elif rid == 502 and len(digits) >= 2:
                    passed = digits[-1] - digits[0] == val
            if not passed:
                failed.append(rule['template'].format(val))
        else:
            if not re.search(rule['regex'], password):
                failed.append(rule['desc'])

    return len(failed) == 0, failed