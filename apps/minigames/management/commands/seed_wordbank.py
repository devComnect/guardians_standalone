from django.core.management.base import BaseCommand
from apps.minigames.models import WordBank


WORDS = [
    # (palavra, dica, categoria, dificuldade)

    # ── FÁCIL — 4 letras ──────────────────────────────────
    ('REDE',  'Infraestrutura de comunicação entre dispositivos',        'redes',          'facil'),
    ('NODE',  'Ponto de conexão em uma rede de computadores',            'redes',          'facil'),
    ('ROTA',  'Caminho definido para o tráfego de dados',                'redes',          'facil'),
    ('HASH',  'Função que converte dados em um código de tamanho fixo',  'ciberseguranca', 'facil'),
    ('BYTE',  'Unidade fundamental de informação digital (8 bits)',       'ti',             'facil'),
    ('SPAM',  'Mensagem eletrônica não solicitada enviada em massa',      'ciberseguranca', 'facil'),
    ('WORM',  'Malware que se replica automaticamente pela rede',         'ciberseguranca', 'facil'),
    ('DADO',  'Unidade de informação processável por um sistema',         'ti',             'facil'),
    ('VPNS',  'Redes privadas que criptografam conexões remotas',         'redes',          'facil'),

    # ── FÁCIL — 5 letras ──────────────────────────────────
    ('PORTA', 'Canal de comunicação lógico em um sistema (ex: 443)',     'redes',          'facil'),
    ('SENHA', 'Segredo usado para autenticar um usuário',                 'ciberseguranca', 'facil'),
    ('CHAVE', 'Elemento criptográfico para proteger dados',               'ciberseguranca', 'facil'),
    ('TOKEN', 'Credencial temporária usada para autenticação',            'ciberseguranca', 'facil'),
    ('VIRUS', 'Programa malicioso que se replica em arquivos do sistema', 'ciberseguranca', 'facil'),
    ('PATCH', 'Atualização aplicada para corrigir vulnerabilidades',      'ti',             'facil'),
    ('LOGIN', 'Processo de autenticação em um sistema ou plataforma',     'ti',             'facil'),
    ('ADMIN', 'Usuário com nível máximo de privilégio no sistema',        'ti',             'facil'),
    ('PROXY', 'Servidor intermediário entre cliente e destino na rede',   'redes',          'facil'),
    ('HTTPS', 'Protocolo de transferência segura via TLS/SSL',            'redes',          'facil'),
    ('CLONE', 'Cópia exata de um sistema ou disco rígido',               'ti',             'facil'),

    # ── MÉDIO — 6 letras ──────────────────────────────────
    ('ATAQUE', 'Ação maliciosa direcionada a um sistema ou rede',         'ciberseguranca', 'medio'),
    ('BACKUP', 'Cópia de segurança de dados críticos',                    'ti',             'medio'),
    ('TROJAN', 'Malware disfarçado de software legítimo',                 'ciberseguranca', 'medio'),
    ('BOTNET', 'Rede de dispositivos infectados controlados remotamente', 'ciberseguranca', 'medio'),
    ('FRAUDE', 'Ato desonesto para obter vantagem indevida',              'politicas',      'medio'),
    ('HACKER', 'Especialista em explorar vulnerabilidades de sistemas',   'ciberseguranca', 'medio'),
    ('KERNEL', 'Núcleo central do sistema operacional',                   'ti',             'medio'),
    ('COOKIE', 'Arquivo armazenado pelo navegador para rastrear sessões', 'ti',             'medio'),
    ('SWITCH', 'Dispositivo que interliga segmentos de rede',             'redes',          'medio'),
    ('ROUTER', 'Dispositivo que encaminha pacotes entre redes distintas', 'redes',          'medio'),
    ('BUFFER', 'Área temporária de armazenamento de dados em memória',    'ti',             'medio'),
    ('ACESSO', 'Permissão concedida para utilizar um recurso ou sistema', 'politicas',      'medio'),
    ('CIFRAR', 'Transformar dados em formato ilegível por criptografia',  'ciberseguranca', 'medio'),


    # ── MÉDIO — 7 letras ──────────────────────────────────
    ('MALWARE', 'Categoria de software malicioso projetado para causar dano', 'ciberseguranca', 'medio'),
    ('ROOTKIT', 'Ferramenta que oculta presença de malware no sistema',        'ciberseguranca', 'medio'),
    ('SPYWARE', 'Software que espiona e envia atividades do usuário',          'ciberseguranca', 'medio'),
    ('EXPLOIT', 'Código que aproveita uma vulnerabilidade específica',         'ciberseguranca', 'medio'),
    ('PAYLOAD', 'Parte maliciosa e ativa executada por um malware',            'ciberseguranca', 'medio'),
    ('PRIVADO', 'Dado ou recurso restrito a pessoas autorizadas',              'politicas',      'medio'),
    ('CIFRADO', 'Dado que passou por algoritmo criptográfico',                 'ciberseguranca', 'medio'),


    # ── DIFÍCIL — 8+ letras ───────────────────────────────
    ('PHISHING',   'Ataque de engenharia social via e-mail falso',              'ciberseguranca', 'dificil'),
    ('FIREWALL',   'Barreira de proteção entre redes internas e externas',      'ciberseguranca', 'dificil'),
    ('SPOOFING',   'Falsificação de identidade em comunicações digitais',        'ciberseguranca', 'dificil'),
    ('SNIFFING',   'Interceptação e análise do tráfego de rede',                'ciberseguranca', 'dificil'),
    ('KEYLOGGER',  'Programa que registra teclas digitadas pelo usuário',        'ciberseguranca', 'dificil'),
    ('BIOMETRIA',  'Identificação por características físicas únicas',           'ciberseguranca', 'dificil'),
    ('PROTOCOLO',  'Conjunto de regras para comunicação entre sistemas',         'redes',          'dificil'),
    ('RANSOMWARE', 'Malware que sequestra dados e exige pagamento de resgate',   'ciberseguranca', 'dificil'),
    ('ENGENHARIA', 'Manipulação psicológica de pessoas para obter acesso',       'ciberseguranca', 'dificil'),
    ('CRIPTOGRAFIA','Ciência de proteger informações por codificação',           'ciberseguranca', 'dificil'),
    ('VULNERABILIDADE','Falha que pode ser explorada por um atacante',           'ciberseguranca', 'dificil'),
    ('MONITORAMENTO','Acompanhamento contínuo de sistemas e redes',              'ti',             'dificil'),
    ('CRIPTOGRAFAR','Transformar dados em formato seguro e ilegível',            'ciberseguranca', 'dificil'),
    ('TUNELAMENTO','Encapsulamento de um protocolo dentro de outro',           'redes',          'dificil'),
    ('VAZAMENTO','Exposição não autorizada de dados confidenciais',       'ciberseguranca', 'dificil'),
]


class Command(BaseCommand):
    help = 'Popula o banco de palavras com termos de segurança e TI'

    def handle(self, *args, **kwargs):
        created = 0
        skipped = 0

        for palavra, dica, categoria, dificuldade in WORDS:
            _, was_created = WordBank.objects.get_or_create(
                palavra=palavra.upper(),
                defaults={
                    'dica':        dica,
                    'categoria':   categoria,
                    'dificuldade': dificuldade,
                }
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Seed concluído: {created} palavra(s) criadas, {skipped} já existiam.'
        ))