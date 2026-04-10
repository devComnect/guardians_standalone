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
    108: {"id": 108, "diff": "easy",   "desc": "Pelo menos uma letra minúscula.",                      "regex": r"[a-z]"},
    109: {"id": 109, "diff": "easy",   "desc": "Pelo menos dois números.",                             "regex": r"(?:\d.*){2}"},
    110: {"id": 110, "diff": "easy",   "desc": "Deve terminar com um número.",                         "regex": r"\d$"},
    111: {"id": 111, "diff": "easy",   "desc": "Deve conter a letra Z.",                               "regex": r"[Zz]"},
    112: {"id": 112, "diff": "easy",   "desc": "Um tipo de arquivo de imagem conhecido (PNG, JPG, GIF).",     "regex": r"(PNG|JPG|GIF)"},
    # MÉDIO
    201: {"id": 201, "diff": "medium", "desc": "Deve conter o ano atual (2026).",                      "regex": r"2026"},
    202: {"id": 202, "diff": "medium", "desc": "Deve começar com 'CMD' ou 'ROOT'.",                    "regex": r"^(CMD|ROOT)"},
    203: {"id": 203, "diff": "medium", "desc": "Deve terminar com três números.",                      "regex": r"\d{3}$"},
    204: {"id": 204, "diff": "medium", "desc": "Não pode conter espaços.",                             "regex": r"^[^ ]*$"},
    205: {"id": 205, "diff": "medium", "desc": "Deve conter uma extensão de script (.PY, .SH, .BAT).", "regex": r"\.(PY|SH|BAT)"},
    206: {"id": 206, "diff": "medium", "desc": "Deve conter 'ADMIN' ou 'USER'.",                       "regex": r"(ADMIN|USER)"},
    207: {"id": 207, "diff": "medium", "desc": "Deve conter o operador matemático '+' ou '='.",        "regex": r"[+=]"},
    209: {"id": 209, "diff": "medium", "desc": "Deve conter três caracteres repetidos em sequência.",  "regex": r"(.)\1\1"},
    210: {"id": 210, "diff": "medium", "desc": "Deve conter exatamente 22 caracteres.",                "regex": r"^.{22}$"},
    211: {"id": 211, "diff": "medium", "desc": "Deve conter 'HACK' ou 'CODE'.",                        "regex": r"(HACK|CODE)"},
    212: {"id": 212, "diff": "medium", "desc": "Deve conter pelo menos um colchete [ ou ].",           "regex": r"[\[\]]"},
    213: {"id": 213, "diff": "medium", "desc": "Deve conter 'BUG' ou 'FIX'.",                          "regex": r"(BUG|FIX)"},
    214: {"id": 214, "diff": "medium", "desc": "Um navegador WEB famoso.",                             "regex": r"(EXPLORER|EDGE|CHROME|FIREFOX|SAFARI)"},
    # DIFÍCIL
    301: {"id": 301, "diff": "hard",   "desc": "Deve conter um protocolo (HTTP, FTP, SSH, TELNET).",   "regex": r"(HTTP|FTP|SSH|TELNET)"},
    302: {"id": 302, "diff": "hard",   "desc": "Deve conter 'SUDO' em maiúsculas.",                    "regex": r"SUDO"},
    303: {"id": 303, "diff": "hard",   "desc": "Deve conter um numeral romano (I, V, X, L, C).",       "regex": r"[IVXLC]"},
    304: {"id": 304, "diff": "hard",   "desc": "Deve conter uma porta comum (80, 443, 21, 22).",       "regex": r"(80|443|21|22)"},
    305: {"id": 305, "diff": "hard",   "desc": "Deve conter um comando SQL (SELECT, DROP, INSERT).",   "regex": r"(SELECT|DROP|INSERT)"},
    306: {"id": 306, "diff": "hard",   "desc": "Deve conter um formato de email básico (@dominio).",   "regex": r"@\w+\."},
    307: {"id": 307, "diff": "hard",   "desc": "Deve conter 'TRUE' ou 'FALSE'.",                       "regex": r"(TRUE|FALSE)"},
    308: {"id": 308, "diff": "hard",   "desc": "Deve conter um comando Linux (LS, CD, MKDIR, RM).",    "regex": r"(LS|CD|MKDIR|RM)"},
    309: {"id": 309, "diff": "hard",   "desc": "Deve conter 'NULL' ou 'VOID'.",                        "regex": r"(NULL|VOID)"},
    310: {"id": 310, "diff": "hard",   "desc": "Deve conter uma extensão de arquivo (.EXE ou .DLL).",  "regex": r"\.(EXE|DLL)"},
    311: {"id": 311, "diff": "hard",   "desc": "Deve conter 'BUG' ou 'FIX' seguido de um número.",     "regex": r"(BUG|FIX)\d"},
    312: {"id": 312, "diff": "hard",   "desc": "Uma linguagem de programação (PYTHON, JAVA, RUBY).",    "regex": r"(PYTHON|JAVA|RUBY)"},
    # INSANO
    401: {"id": 401, "diff": "insane", "desc": "Formato de IP (Ex: 192.168.1.1).",                     "regex": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"},
    402: {"id": 402, "diff": "insane", "desc": "Código Hexadecimal de cor (Ex: #FFFFFF).",             "regex": r"#[0-9A-Fa-f]{6}"},
    403: {"id": 403, "diff": "insane", "desc": "Endereço MAC parcial (Ex: FF:FF:FF).",                 "regex": r"[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}"},
    404: {"id": 404, "diff": "insane", "desc": "Deve conter uma tag HTML (Ex: <DIV>, <BR>).",          "regex": r"<[A-Z]+>"},
    405: {"id": 405, "diff": "insane", "desc": "Deve conter formato de versão (vX.X.X).",              "regex": r"v\d+\.\d+\.\d+"},
    407: {"id": 407, "diff": "insane", "desc": "Valor em formato de dólar ($99,99).",                  "regex": r"\$\d+\,\d{2}"},
    408: {"id": 408, "diff": "insane", "desc": "NÃO pode conter as vogais A ou I.",                    "regex": r"^[^AIai]*$"},
    409: {"id": 409, "diff": "insane", "desc": "NÃO pode conter os números (0,4,6,8).",                 "regex": r"^[^0468]*$"},
    410: {"id": 410, "diff": "insane", "desc": "Um sistema operacional amplamente conhecido.",          "regex": r"(WINDOWS|LINUX|KALI)"},
    # DINÂMICAS (math)
    500: {"id": 500, "diff": "medium", "template": "A soma de todos os números deve ser {}.",          "js_type": "sum"},
    501: {"id": 501, "diff": "hard",   "template": "O primeiro número menos o último deve ser {}.",    "js_type": "sub_first_last"},
    502: {"id": 502, "diff": "hard",   "template": "O último número menos o primeiro deve ser {}.",    "js_type": "sub_last_first"},
}

# Pares de regras que não podem ser sorteadas juntas
INCOMPATIBLE_RULES = [
    (408, 213),  # sem A/I vs BUG/FIX — FIX ok, BUG ok, mas seguro manter
    (408, 311),  # sem A/I vs BUG/FIX+num — mesmo caso
]


def _are_compatible(selected_ids):
    """Retorna False se algum par incompatível estiver nos ids selecionados."""
    id_set = set(selected_ids)
    for a, b in INCOMPATIBLE_RULES:
        if a in id_set and b in id_set:
            return False
    return True


def generate_rules_sequence(config):
    max_attempts = 100

    for _ in range(max_attempts):
        selected = []

        by_diff = {'easy': [], 'medium': [], 'hard': [], 'insane': []}
        for k, v in PASSWORD_RULES_DB.items():
            if k < 500:
                by_diff[v['diff']].append(k)

        def sample(pool, n):
            return random.sample(pool, min(len(pool), n))

        static_ids = (
            sample(by_diff['easy'],   config.rules_count_easy) +
            sample(by_diff['medium'], config.rules_count_medium) +
            sample(by_diff['hard'],   config.rules_count_hard) +
            sample(by_diff['insane'], config.rules_count_insane)
        )

        if not _are_compatible(static_ids):
            continue

        # Dígitos disponíveis considerando restrições ativas
        # 409: não pode conter 0,4,6,8 → dígitos válidos: {1,2,3,5,7,9}
        restricted_digits = 409 in static_ids

        math_ids = [k for k in PASSWORD_RULES_DB if k >= 500]
        if math_ids and config.rules_count_math > 0:
            for _ in range(config.rules_count_math):
                mid = random.choice(math_ids)
                if mid == 500:
                    # soma: com restrição, usar range menor e alcançável
                    val = random.randint(3, 18) if restricted_digits else random.randint(15, 50)
                else:
                    # diferença: resultado não precisa ser dígito da senha, range normal
                    val = random.randint(1, 8)
                selected.append(f"{mid}:{val}")

        selected += [str(i) for i in static_ids]
        random.shuffle(selected)
        return selected

    # fallback: retorna sem insane para garantir compatibilidade
    selected = []
    for diff in ['easy', 'medium', 'hard']:
        pool = [k for k, v in PASSWORD_RULES_DB.items() if k < 500 and v['diff'] == diff]
        n = getattr(config, f'rules_count_{diff}')
        selected += [str(i) for i in random.sample(pool, min(len(pool), n))]
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