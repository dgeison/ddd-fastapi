# Construindo um Monólito Modular com FastAPI e DDD

Documento vivo — atualizado a cada passo da construção do projeto `track-money`.

---

## O que é um Monólito Modular?

Um monólito modular é uma aplicação que roda como um único processo (deploy simples como um monólito tradicional), mas com o código organizado em módulos bem delimitados que se comunicam por interfaces claras — como se fossem serviços separados, mas sem a complexidade de microserviços.

**Vantagens:**
- Deploy e operação simples (um processo só)
- Boundaries claros entre domínios desde o início
- Fácil de evoluir para microserviços se necessário
- Sem overhead de rede entre módulos

---

## Stack escolhida

| Ferramenta | Papel |
|---|---|
| `uv` | Gerenciador de pacotes e ambiente virtual |
| `FastAPI` | Framework web assíncrono |
| `uvicorn` | Servidor ASGI |

---

## Passo 1 — Criar o projeto com uv

```bash
uv init track-money
cd track-money
```

O `uv` cria automaticamente:
- `pyproject.toml` — metadados e dependências do projeto
- `uv.lock` — lockfile para reprodutibilidade exata do ambiente
- `.venv/` — ambiente virtual isolado

**Por que uv?** É ordens de magnitude mais rápido que pip/poetry e unifica gerenciamento de pacotes, ambiente virtual e execução de scripts em uma única ferramenta.

---

## Passo 2 — Adicionar dependências web

```bash
uv add fastapi uvicorn
```

Isso atualiza o `pyproject.toml` e instala as libs no ambiente virtual local.

**`pyproject.toml` resultante:**
```toml
[project]
name = "track-money"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "fastapi>=0.136.0",
    "uvicorn>=0.44.0",
]
```

---

## Passo 3 — Criar a estrutura base

```
track-money/
├── app/
│   └── main.py       ← ponto de entrada da aplicação
├── pyproject.toml
└── uv.lock
```

A pasta `app/` deve ficar **dentro** de `track-money/` — onde está o `pyproject.toml`. Isso garante que o Python encontre o módulo `app` ao rodar `uvicorn app.main:app` a partir da raiz do projeto.

> Ter `app/` fora de `track-money/` gera `ModuleNotFoundError: No module named 'app'` porque o Python não encontra o pacote no `sys.path` quando o comando é executado de dentro do diretório do projeto.

---

## Passo 4 — Servidor FastAPI com health check

**`app/main.py`:**
```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Track Money API",
    description="API for tracking money and expenses",
    version="1.0.0",
)

@app.get("/health")
async def health_check():
    return JSONResponse(status_code=200, content={"status": "ok"})
```

Para rodar em desenvolvimento:
```bash
uv run uvicorn app.main:app --reload
```

Ou diretamente pelo Python (útil para debug e deploy simples):
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Por que `0.0.0.0`?** Faz o servidor escutar em todas as interfaces de rede, necessário para acessar de fora do container ou da VM. Em desenvolvimento local `127.0.0.1` seria suficiente, mas `0.0.0.0` é o padrão para ambientes Docker/WSL.

**Por que `/health` e não `/`?** Endpoints de health check têm uma rota semântica dedicada — load balancers, orquestradores (Kubernetes, Docker Swarm) e ferramentas de monitoramento esperam bater em `/health` ou `/healthz` para verificar se o serviço está vivo. Usar `/` misturaria preocupações da infra com a lógica da aplicação.

**Por que `JSONResponse` explícito?** Permite controle direto do `status_code` — retornar `200` garante que o monitor reconheça o serviço como saudável. FastAPI infere o status code por padrão, mas para health checks é melhor ser explícito.

**Por que `async def`?** FastAPI é construído sobre ASGI — funções assíncronas permitem lidar com muitas requisições simultâneas sem bloquear o event loop, essencial para APIs que fazem I/O (banco de dados, APIs externas).

---

## Passo 5 — Dependências de banco e autenticação

```bash
uv add sqlalchemy psycopg2-binary passlib[bcrypt] python-jose
```

**`pyproject.toml` atualizado:**
```toml
dependencies = [
    "fastapi>=0.136.0",
    "passlib[bcrypt]>=1.7.4",
    "psycopg2-binary>=2.9.11",
    "python-jose>=3.5.0",
    "sqlalchemy>=2.0.49",
    "uvicorn>=0.44.0",
]
```

| Lib | Papel |
|---|---|
| `sqlalchemy` | ORM — mapeia classes Python para tabelas do banco |
| `psycopg2-binary` | Driver PostgreSQL — conector entre SQLAlchemy e o banco |
| `passlib[bcrypt]` | Hashing de senhas com bcrypt — nunca armazene senha em texto puro |
| `python-jose` | Geração e validação de tokens JWT — autenticação stateless |

**Por que `psycopg2-binary` e não `psycopg2`?** A versão `-binary` inclui as libs nativas compiladas — sem precisar de `libpq-dev` instalado no sistema. Ideal para desenvolvimento; em produção, `psycopg2` compilado localmente pode ser mais performático.

**Por que JWT (python-jose)?** Em um monólito modular, JWT permite que cada módulo valide tokens de forma independente, sem precisar consultar um serviço central de sessões — alinha com a autonomia dos módulos.

---

## Passo 7 — Arquivo `.http` para testar endpoints

```
track-money/
├── app/
│   └── main.py
├── endpoint.http     ← testes de API direto no editor
├── pyproject.toml
└── uv.lock
```

O arquivo `endpoint.http` é usado pela extensão **REST Client** do VSCode — permite disparar requisições HTTP diretamente do editor, sem precisar de Postman ou curl.

**Exemplo de uso (`endpoint.http`):**
```http
@baseUrl = http://localhost:8000

### Health Check Endpoint
GET {{baseUrl}}/health

### User Registration Endpoint
POST {{baseUrl}}/users
Content-Type: application/json
{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "password": "12345678"
}
```

A variável `@baseUrl` centraliza a URL base — trocar de porta ou ambiente (local → staging) é uma mudança em um único lugar. A sintaxe `{{baseUrl}}` (sem `@`) é como o REST Client interpola a variável na URL.

**Por que isso importa no monólito modular?** À medida que novos módulos e endpoints forem criados, o `endpoint.http` serve como documentação viva e executável da API — cada módulo pode ter seu próprio bloco de exemplos no arquivo.

---

## Passo 8 — Primeiro módulo: `authentication`

```
track-money/
└── app/
    ├── authentication/       ← bounded context de autenticação
    │   ├── _user.py          ← entidade interna (privada ao módulo)
    │   └── _password.py       ← serviço de hashing
    └── main.py
```

O módulo `authentication` é o primeiro **bounded context** do monólito modular — ele delimita tudo que é responsabilidade do domínio de autenticação: usuários, senhas, tokens.

**Convenção de privacidade com underscore:**

Python não tem modificadores de acesso (`private`, `internal`) como Java ou C#. A convenção de prefixar com `_` (ex: `_User`) sinaliza para outros desenvolvedores: "esta classe é interna ao bounded context `authentication` — não a importe diretamente de outros módulos".

Isso reforça o isolamento entre bounded contexts: outro módulo (ex: `transactions`) não deve conhecer os detalhes internos de `User` — deve interagir com o contexto de autenticação apenas pela sua interface pública (um serviço, um schema, um repositório exposto intencionalmente).

**`app/authentication/_user.py`:**
```python
from sqlalchemy import Column, Integer, String

from app.domain_exception import DomainException
from app.authentication._password import get_password_hash
from app.infra.database import Base

class _User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "authentication"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)
    hashed_password = Column(String(512), nullable=False)

    def __init__(self, name: str, email: str, password: str):
        DomainException.validate(
            name and len(name) <= 128,
            "Name must be a non-empty string with a maximum length of 128 characters.",
        )
        self.name = name
        DomainException.validate(
            email and len(email) <= 128,
            "Email must be a non-empty string with a maximum length of 128 characters.",
        )
        self.email = email
        DomainException.validate(
            password and len(password) >= 8,
            "Password must be a non-empty string with a minimum length of 8 characters.",
        )
        self.hashed_password = get_password_hash(password)

    def verify_password(self, password: str) -> bool:
        return verify_password(password, self.hashed_password)
```

Decisões de design relevantes:

| Campo/Config | Decisão | Motivo |
|---|---|---|
| `__table_args__ = {"schema": "authentication"}` | Schema PostgreSQL por módulo | Isola as tabelas de cada domínio no banco — `authentication.users`, `transactions.entries`, etc. |
| `email` | `unique=True, index=True, nullable=False` | Email é identidade do usuário — único, indexado e obrigatório |
| `name`, `email`, `hashed_password` | `nullable=False` | Constraints no banco como segunda linha de defesa — mesmo que o domínio já valide, o banco garante integridade mesmo acessos diretos (migrations, scripts) |
| `hashed_password` | `String(512)` | Bcrypt gera hashes de ~60 chars, mas 512 dá margem para outros algoritmos |
| `hashed_password` | prefixo `hashed_` | Convenção que deixa claro no código que NUNCA se armazena senha em texto puro |

**`verify_password` como método da entidade:**

```python
def verify_password(self, password: str) -> bool:
    return verify_password(password, self.hashed_password)
```

A verificação de senha vive na própria entidade `_User` — quem tem a senha é `_User`, então quem sabe verificá-la também deve ser `_User`. Isso é encapsulamento: o `hashed_password` não precisa "vazar" para fora da entidade para ser comparado.

Uso natural no caso de login:
```python
user = repository.get_by_email(email)
if not user or not user.verify_password(password):
    raise DomainException("Invalid credentials")
```

Alternativa menos coesa seria expor o `hashed_password` e chamar `verify_password(plain, user.hashed_password)` de fora — funciona, mas quebra o encapsulamento e espalha lógica de autenticação pelos serviços.

**Exceção de domínio própria (`app/domain_exception.py`):**

```python
class DomainException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message

    @staticmethod
    def validate(condition: bool, message: str):
        if not condition:
            raise DomainException(message)
```

`DomainException` substitui o `ValueError` genérico do Python e ganha um método `validate()` estático que elimina o `if/raise` repetitivo nas entidades. As validações do `User` passam a ser expressas de forma declarativa:

```python
# Antes — imperativo
if not name or len(name) > 128:
    raise DomainException("Name must be...")

# Depois — declarativo
DomainException.validate(bool(name) and len(name) <= 128, "Name must be...")
```

Isso permite que a camada de apresentação (routers FastAPI) capture erros de domínio de forma específica — sem confundir com erros de infraestrutura ou bugs.

```python
# No router, é possível tratar separadamente:
except DomainException as e:
    raise HTTPException(status_code=422, detail=e.message)
except Exception:
    raise HTTPException(status_code=500, detail="Internal error")
```

**Estrutura atual do `app/`:**
```
app/
├── domain_exception.py       ← exceção base compartilhada entre módulos
├── authentication/
│   └── user.py
└── main.py
```

`domain_exception.py` fica na raiz do `app/` porque é compartilhada entre módulos — é uma peça de infraestrutura do domínio, não pertence a nenhum bounded context específico.

**Validação de domínio no construtor:**

A regra de negócio "nome não pode ser vazio nem ultrapassar 128 caracteres" vive dentro da entidade — um `User` inválido nunca chega a existir. Isso é um invariante de domínio: a entidade se protege, independente de quem a instancia.

Alternativa comum (mas problemática) seria validar no router ou no service — dispersando regras de negócio pela aplicação e permitindo que um `User` com nome inválido exista temporariamente em memória.

**Extração do hashing para `__password.py`:**

```python
# app/authentication/__password.py
import bcrypt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

O hashing foi extraído da entidade `User` para um módulo dedicado. Isso segue o **Princípio da Responsabilidade Única (SRP)**: `User` modela o domínio, `_password.py` cuida da criptografia.

`CryptContext` com `deprecated="auto"` permite migrar algoritmos no futuro (ex: bcrypt → argon2) sem mudar o código — hashes antigos continuam sendo verificados, novos usam o algoritmo atual.

**`_User(Base)` — a conexão entre domínio e banco:**

```python
from app.infra.database import Base

class _User(Base):
```

Herdar de `Base` registra `_User` no SQLAlchemy ORM — a partir daí, `__tablename__` e `__table_args__` definem onde a tabela será criada no banco. É o elo entre a entidade de domínio e a infraestrutura de persistência.

**Por que hashear no `__init__` da entidade?**

O `User` aceita a senha em texto puro e já a hasheia internamente — quem cria um `User` nunca precisa se preocupar em chamar `hash_password` manualmente. Isso é **encapsulamento de domínio**: a regra "senha deve ser hasheada" vive dentro da própria entidade, não espalhada pelos serviços que a usam.

**Por que schema por módulo no banco?**

O uso de `schema` do PostgreSQL espelha no banco de dados o mesmo isolamento que os módulos têm no código. Cada domínio "possui" suas tabelas dentro do seu schema — assim como no código cada módulo tem sua própria pasta. Isso facilita:
- Controle de permissões por domínio (`GRANT` por schema)
- Migração futura para microserviços (mover um schema para outro banco)
- Visualização clara de quais tabelas pertencem a qual domínio

**Por que criar um módulo por domínio e não por camada?**

A organização por camada (models/, controllers/, services/) mistura responsabilidades de domínios diferentes no mesmo diretório — um `models/` com User, Transaction e Category juntos dificulta entender onde termina um domínio e começa outro.

A organização por módulo/domínio (authentication/, transactions/, categories/) agrupa tudo que pertence ao mesmo contexto — models, services, routers — dentro do seu próprio diretório. Isso é a base do **DDD (Domain-Driven Design)** aplicado à estrutura de pastas.

---

## Passo 9 — Camada de infraestrutura: banco de dados

```
app/
├── infra/
│   └── database.py     ← configuração do SQLAlchemy e conexão com o banco
├── authentication/
│   ├── _user.py
│   └── _password.py
├── domain_exception.py
└── main.py
```

A pasta `infra/` separa preocupações de infraestrutura (banco, cache, filas) do código de domínio. No DDD, infraestrutura é tudo que não é regra de negócio.

**`app/infra/database.py`:**
```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost:5437/track_money_db"
```

| Elemento | Papel |
|---|---|
| `Base = declarative_base()` | Classe base que todos os models SQLAlchemy herdam — registra metadados das tabelas |
| `SQLALCHEMY_DATABASE_URL` | String de conexão com o PostgreSQL |
| Porta `5437` | Porta não-padrão (padrão é 5432) — provavelmente PostgreSQL rodando em Docker com porta mapeada |

**`app/infra/database.py` completo:**
```python
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

| Elemento | Decisão | Motivo |
|---|---|---|
| `autocommit=False` | Commit manual | Controle explícito de transações — garante que falhas não persistem dados parciais |
| `autoflush=False` | Flush manual | Evita SQL inesperado antes do commit — mais previsível em operações complexas |
| `get_db()` com `yield` | Generator/context manager | O `finally` garante que a sessão é fechada mesmo em caso de exceção — sem vazamento de conexões |

**Como usar no FastAPI (injeção de dependência):**
```python
from fastapi import Depends
from app.infra.database import get_db
from sqlalchemy.orm import Session

@app.post("/users")
def create_user(db: Session = Depends(get_db)):
    # db é aberta, usada, e fechada automaticamente
    ...
```

`Depends(get_db)` faz o FastAPI gerenciar o ciclo de vida da sessão — abre antes do endpoint, fecha após a resposta.

**Funções de inicialização do banco:**
```python
def init_database():
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS authentication"))
        conn.commit()

def reset_database():
    Base.metadata.create_all(bind=engine)
```

| Função | Papel |
|---|---|
| `init_database()` | Cria os schemas PostgreSQL por módulo (`authentication`, etc.) — precisa rodar antes do `create_all` |
| `create_tables()` | Importa os models e cria todas as tabelas registradas no `Base` |

**Por que `init_database` separado?** O `Base.metadata.create_all` cria tabelas, mas não cria schemas. Se o schema não existir, o `create_all` falha. Por isso `init_database` roda primeiro para garantir que os schemas existem.

À medida que novos módulos são adicionados, `create_tables` importa suas entidades e `init_database` cria seus schemas:

```python
def init_database():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS authentication"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS subscription"))  # ← novo módulo
        conn.commit()

def create_tables():
    engine = get_engine()
    from app.authentication._user import User              # noqa: F401
    from app.subscription.plan._plan import Plan           # noqa: F401
    from app.subscription.user._user_plan import UserPlan  # noqa: F401
    from app.movement.bank._bank_account import BankAccount  # noqa: F401
    Base.metadata.create_all(bind=engine)
```

> **Atenção:** `subscription` foi adicionado em `create_tables` mas o schema `subscription` ainda não foi criado em `init_database` — o `create_all` vai falhar com erro de schema inexistente.

**Ordem de execução no startup da aplicação:**
```python
def create_tables():
    from app.authentication._user import _User  # noqa: F401
    Base.metadata.create_all(bind=engine)

init_database()   # 1. cria schemas
create_tables()   # 2. importa models + cria tabelas
```

**Por que importar `_User` dentro de `create_tables`?**

SQLAlchemy só sabe criar tabelas de models que foram importados — classes que herdam de `Base` se registram no momento do import. Se `_User` nunca foi importado antes do `create_all`, o `Base.metadata` estará vazio e nenhuma tabela será criada.

O import dentro da função evita importação circular: `database.py` não precisa conhecer os models no nível do módulo — só no momento em que vai criar as tabelas. O `# noqa: F401` suprime o aviso do linter de "import não utilizado", deixando claro que o import é intencional.

> Renomeações ao longo do desenvolvimento: `reset_database` → `create_database` → `create_tables`. Nome final é o mais preciso.

---

## Passo 10 — Docker Compose para o banco de dados

**`docker_compose.yml`:**
```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: track_money_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: track_money_db
    ports:
      - "5437:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

Para subir o banco:
```bash
docker compose -f docker_compose.yml up -d
```

| Configuração | Decisão | Motivo |
|---|---|---|
| `postgres:15-alpine` | Imagem Alpine | Imagem menor (~80MB vs ~400MB) — suficiente para desenvolvimento |
| `5437:5432` | Porta não-padrão | Evita conflito com PostgreSQL que possa estar instalado localmente na porta 5432 |
| `postgres_data` volume | Volume nomeado | Dados persistem entre restarts do container |
| `./init.sql` montado | Script de inicialização | Executado automaticamente na primeira criação do container — ideal para criar schemas |
| `healthcheck` | Verificação de saúde | Garante que o container só é considerado "pronto" quando o PostgreSQL aceitar conexões |

---

## Passo 11 — Primeiro endpoint: `POST /users`

```
app/
└── authentication/
    ├── _user.py          ← entidade (privada)
    ├── _register_user.py     ← handler do endpoint POST /users (privado)
    └── _password.py       ← serviço de hashing
```

**`app/authentication/_register_user.py`:**
```python
class UserCreate(BaseModel):
    email: str
    password: str
    name: str

def register_user(body: UserCreate, db: Session = Depends(get_db)):
    user = _User(name=body.name, email=body.email, password=body.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return JSONResponse(status_code=201, content=None, headers={"Location": f"/users/{user.id}"})
```

**Padrão adotado:** cada operação (POST, GET, PUT, DELETE) tem seu próprio arquivo prefixado com `_` — `_register_user.py`, `_get_user.py`, etc. Mantém o bounded context coeso e os arquivos pequenos e focados.

| Elemento | Papel |
|---|---|
| `UserCreate(BaseModel)` | Schema Pydantic — valida e deserializa o body da requisição |
| `Depends(get_db)` | Injeta a sessão do banco, gerenciada pelo FastAPI |
| `db.add` → `db.commit` → `db.refresh` | Persiste o `_User` e recarrega o `id` gerado pelo banco |
| `status_code=201` | HTTP 201 Created — semântica correta para criação de recurso |
| `Location: /users/{id}` | Header REST padrão — informa ao cliente onde o recurso criado pode ser encontrado |

---

## Passo 13 — Interface pública do módulo: `route.py`

```
app/authentication/
├── _user.py          ← entidade (privada)
├── _register_user.py     ← handler POST (privado)
├── _password.py       ← hashing (privado)
└── route.py          ← router público ← o que o resto da app enxerga
```

`route.py` **sem** underscore é a fronteira pública do bounded context `authentication`. É o único arquivo que outros módulos e o `main.py` devem importar — tudo com `_` fica encapsulado.

```python
from fastapi import APIRouter
from app.authentication._register_user import register_user

user_router = APIRouter()

user_router.add_api_route(
    "/",
    endpoint=register_user,
    methods=["POST"],
    response_model=None,
    tags=["users"],
    summary="Create a new user",
)
```

**Por que `APIRouter` em vez de registrar direto no `app`?**

Cada módulo declara seu próprio `APIRouter` — o `main.py` apenas inclui os routers dos módulos com `app.include_router(user_router)`. Isso mantém o `main.py` como um orquestrador simples, sem conhecer os detalhes de nenhum domínio.

**Por que a rota é `"/"` e não `"/users"`?**

O prefixo `/users` será definido no `include_router` do `main.py`, separando a responsabilidade: o módulo define *o que faz*, o `main.py` define *em qual caminho* fica montado.

```python
# main.py final esperado
from app.authentication.route import user_router
app.include_router(user_router, prefix="/users")
# resultado: POST /users/  →  register_user
```

---

## Passo 14 — `main.py` como orquestrador

```python
from app.infra.database import init_database, create_tables
from app.authentication.route import user_router

init_database()   # cria schemas
create_tables()   # cria tabelas

app = FastAPI(...)
app.include_router(user_router, prefix="/users", tags=["users"])

@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})
```

O `main.py` é um **orquestrador**: inicializa o banco no startup e monta os routers dos módulos. `init_database()` e `create_tables()` rodam em nível de módulo — executam quando o uvicorn importa `main.py`, antes de qualquer requisição chegar.

**Atenção:** inicialização no nível de módulo funciona bem para desenvolvimento, mas em produção considere usar eventos de lifecycle do FastAPI (`@app.on_event("startup")`) para ter mais controle sobre quando e como o banco é inicializado.

**Logging e handler global de exceções de domínio:**

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    logger.info("DomainException: %s", exc.message)
    return JSONResponse(status_code=400, content={"detail": exc.message})
```

Captura qualquer `DomainException` lançada em qualquer módulo e retorna `400 Bad Request` com a mensagem de negócio. Sem isso, o FastAPI retornaria `500 Internal Server Error` para erros de domínio — confundindo erros esperados com bugs.

**`@app.exception_handler` vs `app.add_exception_handler`:** o decorator é equivalente ao método imperativo, mas é mais idiomático no FastAPI — mesmo estilo dos `@app.get`, `@app.post`.

**Armadilha comum:** qualquer statement entre o decorator e a função quebra o registro. O decorator é aplicado à expressão imediatamente seguinte — se houver um `logger.info(...)` no meio, ele é aplicado ao retorno do `logger.info` (que é `None`), e a função fica sem registro:

```python
# ERRADO — decorator aplicado ao logger.info, não à função
@app.exception_handler(DomainException)
logger.info("...")   # ← isso é tratado como a "função" a decorar
async def domain_exception_handler(...):
    ...

# CORRETO — logger dentro da função
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    logger.info("DomainException: %s", exc.message)
    ...
```

**Por que `logging.getLogger(__name__)`?** Cria um logger com o nome do módulo atual — permite filtrar logs por módulo em ferramentas de observabilidade (Datadog, CloudWatch, etc.) e ajustar o nível de log por módulo sem afetar o restante da aplicação.

| Antes (violação) | Depois (correto) |
|---|---|
| `from app.authentication._user import _User` | `from app.authentication.route import user_router` |
| `main.py` conhecia internals do módulo | `main.py` conhece apenas a interface pública |

**Estrutura final do monólito modular (primeiro módulo completo):**

```
track-money/
└── app/
    ├── infra/
    │   └── database.py           ← engine, sessão, init/reset
    ├── authentication/           ← bounded context
    │   ├── _user.py              ← entidade (privada)
    │   ├── _register_user.py         ← handler POST (privado)
    │   ├── _password.py           ← hashing bcrypt (privado)
    │   └── route.py              ← APIRouter público ← única saída do módulo
    ├── domain_exception.py       ← exceção base compartilhada
    └── main.py                   ← orquestrador: só inclui routers
```

**Fluxo de uma requisição `POST /users`:**
```
HTTP POST /users
  → main.py (include_router prefix="/users")
    → route.py (user_router, endpoint=register_user)
      → _register_user.py (valida body, cria _User, persiste no banco)
        → _user.py (valida invariantes de domínio, hasheia senha)
          → _password.py (bcrypt)
          → database.py (sessão SQLAlchemy)
```

---

## Passo 15 — Padrão Repository

```
app/authentication/
├── _user.py              ← entidade (privada)
├── _register_user.py         ← handler POST (privado)
├── _password.py          ← hashing bcrypt (privado)
├── user_repository.py    ← repositório de persistência
└── route.py              ← APIRouter público
```

**`app/authentication/user_repository.py`:**
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.authentication._user import _User
from app.infra.database import get_db

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user: _User):
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

    def get_by_email(self, email: str) -> _User | None:
        return self.db.query(_User).filter(_User.email == email).first()

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)
```

**`app/authentication/_register_user.py` atualizado:**
```python
def register_user(
    body: UserCreate,
    user_repository: UserRepository = Depends(get_user_repository)
):
    if user_repository.get_by_email(body.email):
        return JSONResponse(status_code=400, content={"detail": "Email already registered"})
    user = _User(name=body.name, email=body.email, password=body.password)
    user_repository.create(user)
    return JSONResponse(status_code=201, content=None, headers={"Location": f"/users/{user.id}"})
```

**O que é o Repository pattern?**

O Repository encapsula toda a lógica de persistência — `db.add`, `db.commit`, `db.refresh` — atrás de uma interface orientada ao domínio. O handler `_register_user.py` passa a falar em termos de domínio (`repository.create(user)`) em vez de termos de infraestrutura (`db.add`, `db.commit`).

**Antes (sem Repository):**
```python
# _register_user.py injetava db e falava direto com SQLAlchemy
def register_user(body: UserCreate, db: Session = Depends(get_db)):
    db.add(user)
    db.commit()
```

**Depois (com Repository):**
```python
# _register_user.py injeta o repositório e fala o idioma do domínio
def register_user(body: UserCreate, user_repository: UserRepository = Depends(get_user_repository)):
    user_repository.create(user)
```

**`get_user_repository` como factory para `Depends`:**

Em vez de injetar `db: Session = Depends(get_db)` diretamente no handler, a factory `get_user_repository` recebe a sessão e devolve o repositório já configurado. O FastAPI resolve a cadeia de dependências automaticamente:

```
Depends(get_user_repository)
  └── Depends(get_db)
        └── SessionLocal() → yield db → db.close()
```

O handler não precisa saber que existe uma sessão de banco — só conhece o repositório.

**`get_by_email` — verificação de unicidade no handler:**

A verificação `if user_repository.get_by_email(body.email)` no handler é uma **validação de negócio que depende de estado externo** (o banco). Ela não pode viver na entidade `_User` porque a entidade não tem acesso à persistência. Esse é o limite natural entre a entidade (invariantes estáticos) e o handler (invariantes que requerem consulta).

**Por que isso importa no DDD?**

| Sem Repository | Com Repository |
|---|---|
| Handler conhece SQLAlchemy | Handler conhece apenas a interface do domínio |
| Trocar banco = alterar handlers | Trocar banco = alterar só o Repository |
| Difícil testar sem banco real | Repositório pode ser mockado nos testes |

---

## Passo 16 — Variáveis de ambiente para configuração

A URL de conexão com o banco saiu do código-fonte e passou para variável de ambiente.

**`.env.exemple`** (template — commitado no repositório):
```
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost:5437/track_money_db"
```

**`app/infra/database.py` atualizado:**
```python
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

engine = create_engine(os.getenv("DATABASE_URL"))
```

**Por que variáveis de ambiente?**

Hardcodar credenciais no código é um risco de segurança — qualquer pessoa com acesso ao repositório veria usuário, senha e host do banco. Com `os.getenv`, a configuração vem do ambiente de execução:

| Ambiente | Como definir |
|---|---|
| Desenvolvimento local | `.env` (não commitado) |
| CI/CD | Secrets do GitHub Actions / GitLab CI |
| Produção | Variáveis do servidor / Kubernetes Secrets |

**Convenção `.env.exemple`:** o arquivo de exemplo é commitado no repositório como documentação — mostra quais variáveis são necessárias sem expor valores reais. Cada desenvolvedor cria seu `.env` local baseado nele.

> **Atenção — inconsistência de nome:** o `.env.exemple` define `SQLALCHEMY_DATABASE_URL` mas o `database.py` lê `DATABASE_URL`. Esses nomes precisam coincidir. O `.env` local deve usar `DATABASE_URL` (o nome que o código lê), ou o código deve ser ajustado para ler `SQLALCHEMY_DATABASE_URL`.

**`python-dotenv` no `database.py`** (solução correta):

```python
# database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()   # ← carrega .env ANTES de criar o engine

Base = declarative_base()
engine = create_engine(os.getenv("DATABASE_URL"))
```

`load_dotenv()` fica em `database.py` porque é onde `os.getenv("DATABASE_URL")` é chamado. O Python executa o código de módulo no momento do import — se `load_dotenv()` estiver em outro arquivo (ex: `main.py`), as variáveis só ficam disponíveis depois que `database.py` já foi importado e o engine já foi criado com `None`.

**Regra:** `load_dotenv()` deve ser chamado no mesmo módulo que consome as variáveis de ambiente, ou em um módulo de configuração importado antes de qualquer outro.

---

## Passo 17 — Inicialização lazy do engine (refatoração em progresso)

O `database.py` está sendo refatorado para não criar o engine no momento do import — em vez disso, o engine será criado sob demanda, após as variáveis de ambiente estarem carregadas.

**Padrão lazy singleton implementado:**

```python
# database.py
import os
from sqlalchemy import Engine, text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

_engine: Engine | None = None       # singleton do engine
_sessionLocal: sessionmaker | None = None  # singleton da factory de sessões

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        if not os.getenv("DATABASE_URL"):
            raise ValueError("DATABASE_URL environment variable is not set")
        _engine = create_engine(os.getenv("DATABASE_URL"))
    return _engine

def get_session_local() -> sessionmaker:
    global _sessionLocal
    if _sessionLocal is None:
        _sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _sessionLocal

def get_db():
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS authentication"))
        conn.commit()

def create_tables():
    engine = get_engine()
    from app.authentication._user import _User  # noqa: F401
    Base.metadata.create_all(bind=engine)
```

**Por que lazy singleton?**

Criar o engine no nível do módulo (`engine = create_engine(...)`) tem problemas:
- Falha no import se `DATABASE_URL` não estiver no ambiente — impossibilita testes unitários sem banco
- Acopla o import do módulo à disponibilidade do banco

Com lazy initialization, o engine só é criado na primeira chamada a `get_engine()` — quando `DATABASE_URL` já está disponível. Imports subsequentes não criam novas conexões (singleton via `global`).

**Detalhe crítico — `get_db()`:**

`get_session_local()` retorna a *factory* (`SessionLocal`), não uma sessão. Para criar uma sessão, a factory precisa ser chamada:

```python
db = get_session_local()()   # get_session_local() → factory → factory() → sessão
```

Um `()` retorna a factory; dois `()()` retornam a sessão.

---

## Passo 18 — Geração de token JWT: `_auth.py`

```
app/authentication/
├── _user.py              ← entidade
├── _register_user.py     ← caso de uso: registrar
├── _auth.py              ← geração de token JWT  ← novo
├── _password.py          ← hashing bcrypt
├── user_repository.py    ← repositório
└── route.py              ← interface pública
```

**`app/authentication/_auth.py`:**
```python
from datetime import datetime, timedelta, timezone
import os
from jose import jwt
from app.authentication._user import _User

def generate_jwt_token(user: _User) -> str:
    expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)

    payload = {
        "sub": user.email,   # subject — identidade principal do token
        "name": user.name,
        "exp": expire,       # expiration — quando o token deixa de ser válido
    }
    token = jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm=os.getenv("ALGORITHM"))
    return token
```

**`get_email_from_token` — validação de token para endpoints protegidos:**

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/token")

def get_email_from_token(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/users/token")),
) -> str:
    try:
        payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=[os.getenv("ALGORITHM")])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        return email
    except Exception:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
```

Essa função é um **dependency** do FastAPI — qualquer endpoint que precise de autenticação pode injetá-la via `Depends(get_email_from_token)`:

```python
@app.get("/me")
def get_me(email: str = Depends(get_email_from_token)):
    # email já validado e extraído do token
    ...
```

| Elemento | Papel |
|---|---|
| `OAuth2PasswordBearer(tokenUrl="/users/token")` | Extrai o token do header `Authorization: Bearer <token>` e mostra o botão "Authorize" no Swagger UI |
| `jwt.decode(...)` | Verifica assinatura e expiração automaticamente |
| `payload.get("sub")` | Extrai o email colocado no `sub` na geração do token |
| `HTTPException(401)` | Retorna `401 Unauthorized` — o status HTTP correto para credenciais inválidas |
| `except Exception` | Captura qualquer erro de decode: token adulterado, expirado, formato inválido |

**Por que `HTTPException` e não `ValueError`?** `ValueError` não é tratado pelo FastAPI — resultaria em `500 Internal Server Error`. `HTTPException` é a forma correta de retornar erros HTTP dentro de endpoints e dependencies.

**Por que `except Exception` e não `except jwt.JWTError`?** Capturar `Exception` é mais defensivo — qualquer falha no decode resulta em `401`, nunca em `500`.

**Por que `algorithms=[...]` é uma lista?** A biblioteca aceita múltiplos algoritmos para validação — útil na migração entre algoritmos (ex: aceitar HS256 e HS512 por um período de transição).

---

**`from datetime import datetime, timedelta, timezone` — por que importar as três?**

| Símbolo | Papel |
|---|---|
| `datetime` | Classe para obter o momento atual: `datetime.now(timezone.utc)` |
| `timedelta` | Representa uma duração: `timedelta(minutes=30)` |
| `timezone` | Fuso horário UTC: `timezone.utc` — garante datetime *aware* (com tz) |

Ao importar diretamente (`from datetime import ...`), o código fica mais limpo: `datetime.now(timezone.utc)` em vez de `datetime.datetime.now(datetime.timezone.utc)`.

**Variáveis de ambiente necessárias** (adicionar ao `.env`):
```
SECRET_KEY=sua-chave-secreta-longa-e-aleatoria
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Evolução da assinatura:**

A função evoluiu de `generate_jwt_token(user_id, secret_key, algorithm)` para `generate_jwt_token(user: _User)` — a entidade é passada diretamente, e a configuração vem do ambiente. Isso simplifica o uso e centraliza a validação das variáveis dentro da função.

**Claims JWT padrão:**

| Claim | Nome | Papel |
|---|---|---|
| `sub` | Subject | Identidade principal — quem é o dono do token (email neste caso) |
| `exp` | Expiration | Timestamp Unix de expiração — bibliotecas JWT validam automaticamente |
| `name` | (custom) | Dado adicional — evita uma consulta ao banco em endpoints que só precisam exibir o nome |

**Por que `exp` importa?** Tokens sem expiração são válidos para sempre — se vazarem, o atacante tem acesso permanente. Com `exp`, o dano é limitado ao tempo de vida do token.

**Por que `_auth.py` privado?**

A geração de token é um detalhe interno do bounded context `authentication` — outros módulos não devem chamar `generate_jwt_token` diretamente. O token será exposto pelo endpoint de login, que é parte da interface pública (`route.py`).

**Próximo passo natural:** criar `_login_user.py` com o caso de uso de login — verificar credenciais com `user.verify_password()` e retornar o token gerado por `generate_jwt_token`.

---

## Passo 19 — Endpoint de login: `_create_token.py`

```
app/authentication/
├── _user.py              ← entidade
├── _register_user.py     ← caso de uso: registrar
├── _create_token.py      ← caso de uso: login / gerar token  ← novo
├── _auth.py              ← geração de token JWT
├── _password.py          ← hashing bcrypt
├── user_repository.py    ← repositório
└── route.py              ← interface pública
```

**`app/authentication/_create_token.py`:**
```python
from fastapi import Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.authentication.user_repository import UserRepository, get_user_repository
from app.authentication._auth import generate_jwt_token


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_token(
    form_data: OAuth2PasswordRequestForm,
    user_repository: UserRepository = Depends(get_user_repository),
) -> TokenResponse:
    user = user_repository.get_by_email(form_data.username)
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})
    if not user.verify_password(form_data.password):
        return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})

    token = generate_jwt_token(user)
    return TokenResponse(access_token=token, token_type="bearer")
```

**`OAuth2PasswordRequestForm` — por que esse padrão?**

O FastAPI tem suporte nativo ao fluxo OAuth2 com username/password. `OAuth2PasswordRequestForm` deserializa um formulário `application/x-www-form-urlencoded` com campos `username` e `password` — o padrão esperado por clientes OAuth2 (incluindo o Swagger UI automático do FastAPI).

```python
async def create_token(
    form_data: OAuth2PasswordRequestForm = Depends(),  # ← Depends() sem argumento
    user_repository: UserRepository = Depends(get_user_repository),
)
```

**Por que `Depends()` sem argumento para o `OAuth2PasswordRequestForm`?**

`OAuth2PasswordRequestForm` é uma classe que o FastAPI sabe instanciar automaticamente — ela lê o body do request como form data. `Depends()` sem argumento é um atalho para `Depends(OAuth2PasswordRequestForm)`, informando ao FastAPI para injetar uma instância dessa classe.

**Por que `username` e não `email`?** O campo se chama `username` por convenção OAuth2, mas pode conter o email — é só um nome de campo de formulário.

**Fluxo de autenticação:**

```
POST /auth/token  (form: username=email, password=senha)
  → busca usuário por email no banco
  → se não existe → 401
  → verifica senha com user.verify_password()
  → se errada → 401
  → gera JWT com generate_jwt_token(user)
  → retorna { access_token, token_type: "bearer" }
```

**Por que retornar a mesma mensagem para email inválido e senha errada?**

`"Invalid credentials"` para os dois casos é uma decisão de segurança deliberada — não revelar ao atacante se o email existe no sistema. Se a mensagem fosse diferente ("Email not found" vs "Wrong password"), facilitaria ataques de enumeração de usuários.

**`TokenResponse(BaseModel)` — schema de resposta:**

| Campo | Valor |
|---|---|
| `access_token` | O JWT gerado |
| `token_type` | `"bearer"` — tipo padrão OAuth2, informa ao cliente como enviar o token (`Authorization: Bearer <token>`) |

**`route.py` atualizado — três endpoints registrados:**

```python
from app.authentication._register_user import register_user
from app.authentication._create_token import create_token
from app.authentication._get_user_profile import get_user_profile

user_router = APIRouter()

user_router.add_api_route("/", endpoint=register_user, methods=["POST"], ...)
user_router.add_api_route("/token", endpoint=create_token, methods=["POST"], ...)
user_router.add_api_route("/profile", endpoint=get_user_profile, methods=["GET"], response_model=UserProfileResponse, ...)
```

| Endpoint | Caso de uso | Autenticação |
|---|---|---|
| `POST /users/` | Registrar novo usuário | Não |
| `POST /users/token` | Autenticar e receber JWT | Não |
| `GET /users/profile` | Perfil do usuário autenticado | **Sim** — JWT obrigatório |

O `route.py` continua sendo a única saída pública do bounded context. Cada caso de uso tem seu próprio arquivo privado com prefixo `_`.

---

## Passo 20 — Endpoint protegido: `_get_user_profile.py`

```
app/authentication/
├── _user.py                ← entidade
├── _register_user.py       ← caso de uso: registrar
├── _create_token.py        ← caso de uso: login / gerar token
├── _get_user_profile.py    ← caso de uso: perfil autenticado  ← novo
├── _auth.py                ← geração/validação JWT
├── _password.py            ← hashing bcrypt
├── user_repository.py      ← repositório
└── route.py                ← interface pública
```

**`app/authentication/_get_user_profile.py`:**
```python
from fastapi.params import Depends
from pydantic import BaseModel
from app.authentication._auth import get_email_from_token
from app.authentication.user_repository import get_user_repository

class UserProfileResponse(BaseModel):
    name: str
    email: str

    class Config:
        from_attributes = True  # Pydantic v2: lê atributos de objetos SQLAlchemy

async def get_user_profile(
    email: str = Depends(get_email_from_token),  # valida JWT e extrai email
    user_repository = Depends(get_user_repository),
) -> UserProfileResponse:
    user = user_repository.get_by_email(email)
    return user
```

**Fluxo da requisição autenticada:**

```
GET /users/profile
  Authorization: Bearer <jwt_token>
    → FastAPI extrai o token do header (OAuth2PasswordBearer)
      → get_email_from_token() valida o JWT e extrai o email
        → get_by_email(email) busca o usuário no banco
          → retorna UserProfileResponse(name, email)
```

**Por que `Depends(get_email_from_token)` em vez de receber o token diretamente?**

O FastAPI resolve a cadeia de dependencies automaticamente:
1. `OAuth2PasswordBearer` extrai o token do header
2. `get_email_from_token` valida o token e retorna o email
3. `get_user_profile` recebe o email já validado

Isso é **composição de dependencies** — cada peça tem uma responsabilidade e pode ser reutilizada em qualquer endpoint.

**`UserProfileResponse` — por que um schema de resposta separado?**

Nunca retorne a entidade `_User` diretamente — ela contém `hashed_password`. O schema `UserProfileResponse` expõe apenas os campos que o cliente precisa ver, garantindo que dados sensíveis nunca vazem na resposta.

**`from_attributes = True`** permite que o Pydantic leia os atributos de um objeto SQLAlchemy (`_User`) diretamente, sem precisar converter manualmente para dict.

---

## Passo 21 — Consolidação de privacidade no módulo `authentication`

Duas renomeações para alinhar com a convenção de bounded contexts:

| Antes | Depois | Motivo |
|---|---|---|
| `_user.py` → `class _User` | `_user.py` → `class User` | Classe pode ser referenciada internamente sem confusão com "privado" |
| `user_repository.py` | `_user_repository.py` | Repositório é detalhe interno — ninguém fora deve instanciá-lo diretamente |

**Estrutura final do módulo `authentication`:**
```
app/authentication/
├── _user.py              ← entidade User (sem underscore na classe, arquivo ainda privado)
├── _user_repository.py   ← repositório (privado — acesso via get_user_repository())
├── _register_user.py     ← caso de uso: registrar
├── _create_token.py      ← caso de uso: login / gerar token
├── _get_user_profile.py  ← caso de uso: perfil autenticado
├── _auth.py              ← geração/validação JWT
├── _password.py          ← hashing bcrypt
└── route.py              ← única interface pública
```

A regra do bounded context `authentication`:
- **Arquivos `_`** → privados, nunca importados por outros módulos
- **`route.py`** → única porta de entrada (registra os endpoints)
- Outros módulos (`subscription`, etc.) **não importam nada** de `authentication` — recebem apenas dados primitivos (email, user_id) via JWT ou parâmetros de rota

---

## Passo 22 — Arquivos `__init__.py`

```
app/
├── __init__.py                  ← novo
├── infra/
│   └── __init__.py              ← novo
└── authentication/
    └── __init__.py              ← novo
```

`__init__.py` marca um diretório como **pacote Python** — sem ele, o Python não reconhece a pasta como módulo importável.

**Por que só agora?** Em versões modernas do Python (3.3+) existem os *namespace packages* — pastas sem `__init__.py` que ainda funcionam como módulos em muitos casos. Por isso o projeto rodou até aqui sem eles. Adicioná-los agora é uma boa prática que:
- Garante compatibilidade com ferramentas mais antigas
- Torna explícito que a pasta é um pacote intencional
- Permite definir exports públicos do módulo futuramente (`__all__ = [...]`)

O `app/authentication/__init__.py` foi além do marcador vazio — define a interface pública do módulo:

```python
# app/authentication/__init__.py
from .route import user_router

__all__ = ["user_router"]
```

**Por que isso importa?**

`__all__` declara explicitamente o que o módulo exporta. Com isso, o `main.py` pode importar de forma mais limpa:

```python
# Antes — main.py conhecia a estrutura interna do módulo
from app.authentication.route import user_router

# Depois — main.py importa da interface pública do pacote
from app.authentication import user_router
```

**`main.py` atualizado:**
```python
from app.authentication import user_router  # ← interface pública
```

O `main.py` agora é um orquestrador puro — não conhece nenhum detalhe interno do módulo `authentication`. Se o módulo reorganizar seus arquivos internos, o `main.py` não precisa mudar.

Essa é a **interface pública oficial** do bounded context `authentication`: só o `user_router` é exposto. Todo o resto (`_user.py`, `_auth.py`, `_user_repository.py`, etc.) continua privado — quem importa `app.authentication` só enxerga o que `__all__` declara.

É a versão Python do conceito de encapsulamento de módulo — o equivalente a `export` em TypeScript ou `public` em Java.

**Interface pública expandida — `get_email_from_token` extraído:**

```
app/authentication/
├── get_email_from_token.py   ← público — usado por outros módulos
├── _auth.py                  ← privado — geração de token
└── __init__.py               ← exporta user_router + get_email_from_token
```

```python
# app/authentication/__init__.py
from .route import user_router
from .get_email_from_token import get_email_from_token

__all__ = ["user_router", "get_email_from_token"]
```

**Separação de responsabilidades em `_auth.py`:**

Após a extração, `_auth.py` ficou com uma única responsabilidade — gerar tokens:

```
_auth.py              → generate_jwt_token()   (gera JWT)
get_email_from_token.py → get_email_from_token()  (valida JWT)
```

Cada arquivo tem uma razão para mudar: se a lógica de geração mudar, só `_auth.py` é afetado. Se a lógica de validação mudar, só `get_email_from_token.py` é afetado.

**Por que extrair `get_email_from_token` para arquivo público?**

O módulo `subscription` precisa proteger seus endpoints com JWT — mas não pode importar `_auth.py` (privado). Com `get_email_from_token` em arquivo público e exportado pelo `__init__.py`, outros módulos fazem:

```python
# subscription/_create_subscription.py
from app.authentication import get_email_from_token

def create_subscription(
    email: str = Depends(get_email_from_token),  # JWT validado por authentication
    ...
```

O módulo `subscription` usa a validação de JWT sem conhecer nenhum detalhe de como ela funciona internamente em `authentication`. Essa é a fronteira entre bounded contexts em ação.

---

## Passo 23 — Renomeação: `_User` → `User`

A classe `_User` foi renomeada para `User` (sem underscore) em todos os arquivos do módulo `authentication`.

**O que mudou:**
- `_user.py`: `class _User(Base)` → `class User(Base)`
- `user_repository.py`, `_register_user.py`, `_auth.py`: todos os imports e referências atualizados

**Por que remover o underscore?**

O underscore `_` sinalizava "privado ao bounded context." A remoção indica que `User` pode agora ser referenciado por outros módulos — preparação para o módulo `subscription`, que precisará associar uma assinatura a um usuário.

**Atenção — armadilha do DDD:**

Remover o underscore não significa que outros módulos devem importar `User` diretamente. Em DDD, o `subscription` não deve depender da entidade `User` do módulo `authentication`. O correto é:

```python
# ERRADO — subscription conhece internals de authentication
from app.authentication._user import User
class Subscription(Base):
    user: User  # acoplamento direto entre bounded contexts

# CORRETO — subscription só guarda o ID (uma referência por valor)
class Subscription(Base):
    user_email = Column(String, nullable=False)  # só o email, não a entidade
```

O módulo `subscription` receberá o email do usuário via token JWT (já validado pelo middleware) — sem precisar importar nada de `authentication`. Essa é a fronteira entre bounded contexts: **dados primitivos**, não objetos.

---

## Passo 24 — Novo bounded context: `subscription`

```
app/
├── authentication/     ← bounded context existente
└── subscription/       ← novo bounded context
    └── plan/
        └── _plan.py    ← entidade Plan
```

O módulo `subscription` começa com um sub-domínio `plan` — um `Plan` é o produto que o usuário assina (ex: "Plano Básico", "Plano Premium").

**Estrutura aninhada: por que `subscription/plan/`?**

O bounded context `subscription` pode ter múltiplos sub-domínios:
- `plan/` — os planos disponíveis (o catálogo)
- `subscription/` — as assinaturas de cada usuário a um plano

Cada sub-domínio terá sua própria entidade, repositório e casos de uso — seguindo o mesmo padrão do módulo `authentication`.

**`app/subscription/plan/_plan.py`:**
```python
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from app.infra.database import Base

class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = {"schema": "subscription"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(24), unique=True, index=True, nullable=False)
    max_number_accounts = Column(Integer, nullable=False)  # limite de contas por plano
    price = Column(Float, nullable=False)
    is_free = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False)
```

| Campo | Decisão | Motivo |
|---|---|---|
| `name` | `unique=True, String(24)` | Nome do plano é identificador de negócio — curto e único |
| `max_number_accounts` | `Integer` | Cada plano limita quantas contas financeiras o usuário pode criar |
| `is_free` | `Boolean, default=False` | Flag explícita — facilita queries de planos gratuitos sem filtrar por `price=0` |
| `created_at` | `DateTime` | Auditoria — quando o plano foi criado |
| `schema="subscription"` | Schema PostgreSQL | Isola tabelas do domínio `subscription` das demais no banco |

**`__init__` com invariantes de domínio:**
```python
def __init__(self, name: str, max_number_accounts: int, price: float):
    DomainException.validate(name and len(name) <= 24, "Name must be between 1 and 24 characters")
    self.name = name
    DomainException.validate(max_number_accounts > 0, "Max number of accounts must be greater than 0")
    self.max_number_accounts = max_number_accounts
    DomainException.validate(price >= 0.0, "Price must be a non-negative value")
    self.price = price
    self.is_free = price == 0
    self.created_at = datetime.now(timezone.utc)
```

Três invariantes protegem o `Plan`:
- Nome: obrigatório, máximo 24 caracteres
- `max_number_accounts`: sempre positivo — um plano com 0 contas não faz sentido
- `price`: não-negativo — preço negativo é inválido como conceito de negócio

`is_free` é derivado de `price` — nunca inconsistente. `DomainException` é compartilhado entre todos os bounded contexts — definido uma vez em `app/domain_exception.py` e reutilizado em qualquer módulo.

**Como `subscription` se conecta com `authentication`?**

O módulo `subscription` **não importa** nada de `authentication` — exceto `get_email_from_token` para proteger seus endpoints. Quando um usuário assina um plano, o email vem do JWT (já validado), não de uma consulta ao módulo de autenticação:

```python
# _create_subscription.py (futuro)
from app.authentication import get_email_from_token  # único ponto de contato

def create_subscription(
    email: str = Depends(get_email_from_token),  # JWT → email
    plan_id: int = ...,
):
    # cria subscription com user_email=email — sem importar User de authentication
    ...
```

---

---

## Diagramas DDD

### Bounded Context Map

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    CLIENT([Cliente HTTP])

    subgraph AUTH[authentication]
        A_ROUTER[user_router]
        A_TOKEN[get_email_from_token]
        A_QUERY_USER[QueryUserByEmail]
    end

    subgraph SUB[subscription]
        S_ROUTER[subscription_router]
        S_QUERY_PLAN[QueryUserPlan]
    end

    subgraph MOV[movement]
        M_ROUTER[movement_router]
    end

    subgraph SHARED[compartilhado]
        DB[(database.py)]
        EX[DomainException]
    end

    CLIENT -->|POST /users\nPOST /users/token\nGET /users/profile| A_ROUTER
    CLIENT -->|POST /subscriptions/select-plan\nGET /subscriptions/user| S_ROUTER
    CLIENT -->|POST /movement/bank-account| M_ROUTER

    SUB -->|usa JWT| A_TOKEN
    MOV -->|usa JWT| A_TOKEN
    MOV -->|QueryUserByEmail| A_QUERY_USER
    MOV -->|QueryUserPlan| S_QUERY_PLAN

    AUTH --> SHARED
    SUB --> SHARED
    MOV --> SHARED
```

### Entidades por bounded context

```mermaid
%%{init: {'theme': 'dark'}}%%
classDiagram
    direction LR

    class AuthUser {
        +int id
        +str name
        +str email
        +str hashed_password
        +verify_password(password) bool
    }

    class SubUser {
        +int id
        +str name
        +str email
        +add_plan(plan, credit_card)
        -_deactivate_plans()
    }

    class UserPlan {
        +int user_id
        +int plan_id
        +bool active
        +str credit_card
        +datetime created_at
    }

    class Plan {
        +int id
        +str name
        +int max_number_accounts
        +float price
        +bool is_free
    }

    class MovUser {
        +str name
        +str email
        +__composite_values__()
    }

    class BankAccount {
        +int id
        +str name
        +str bank_name
        +str account_number
        +Decimal balance
        +str status
    }

    SubUser "1" *-- "0..*" UserPlan : contem
    UserPlan "0..*" --> "1" Plan : referencia
    BankAccount *-- MovUser : Value Object

    note for AuthUser "authentication.users\nDono da senha"
    note for SubUser "subscription.users\nAggregate Root"
    note for MovUser "Value Object\nEmbutido em BankAccount"
```

### Query Objects — comunicação entre contextos

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    subgraph AUTH[authentication]
        QUE[QueryUserByEmail\nretorna: id, name, email]
    end

    subgraph SUB[subscription]
        QUP[QueryUserPlan\nretorna: plan_id, name, max_accounts]
    end

    subgraph MOV[movement]
        UC[register_bank_account]
    end

    UC -->|.execute email| QUE
    UC -->|.execute email| QUP

    note1[Nenhuma entidade\ncruzou fronteiras]
```

### Fluxo — Login e geração de token

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    autonumber
    actor C as Cliente
    participant R as route.py
    participant CT as _create_token
    participant UR as UserRepository
    participant AU as _auth
    participant DB as PostgreSQL

    C->>R: POST /users/token
    note right of C: form: username + password
    R->>CT: create_token(form_data)
    CT->>UR: get_by_email(username)
    UR->>DB: SELECT FROM authentication.users
    DB-->>UR: User | None
    CT->>CT: user.verify_password(password)
    CT->>AU: generate_jwt_token(user)
    AU-->>CT: JWT assinado
    CT-->>C: access_token
```

### Fluxo — Registrar conta bancária

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    autonumber
    actor C as Cliente
    participant EP as _register_bank_account
    participant QUP as QueryUserPlan
    participant QUE as QueryUserByEmail
    participant BAR as BankAccountRepository
    participant DB as PostgreSQL

    C->>EP: POST /movement/bank-account\nAuthorization: Bearer token
    EP->>QUP: execute(email)
    QUP->>DB: SELECT plano ativo do usuario
    DB-->>QUP: UserPlanResult | None
    alt sem plano ativo
        EP-->>C: 400 - User has no active plan
    end
    EP->>BAR: get_all_by_user(email)
    BAR->>DB: SELECT contas do usuario
    DB-->>BAR: list[BankAccount]
    alt limite atingido
        EP-->>C: 400 - Maximum accounts reached
    end
    EP->>QUE: execute(email)
    QUE->>DB: SELECT FROM authentication.users
    DB-->>QUE: UserByEmailResult
    EP->>EP: BankAccount(user=User VO, ...)
    EP->>BAR: create(bank_account)
    BAR->>DB: INSERT INTO movement.bank_accounts
    EP-->>C: 201 Created
```

---

## Passo 25 — Aggregate Root `User` no módulo `subscription`

```
app/subscription/
├── plan/
│   └── _plan.py
└── user/
    └── _user.py     ← Aggregate Root (privado ao módulo)
```

**`app/subscription/user/_user.py` — Aggregate Root:**
```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.domain_exception import DomainException
from app.infra.database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "subscription"}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), unique=True, index=True, nullable=False)

    user_plans = relationship("UserPlan", back_populates="user")

    def __init__(self, name: str, email: str):
        DomainException.validate(name and len(name) <= 128, "Name must be between 1 and 128 characters.")
        self.name = name
        DomainException.validate(email and len(email) <= 128, "Email must be between 1 and 128 characters.")
        self.email = email

    def add_plan(self, plan: Plan, credit_card: str = None):
        DomainException.validate(plan is not None, "Plan must be provided.")
        if not plan.is_free:
            DomainException.validate(credit_card, "Credit card must be provided for paid plans.")
        self._deactivate_plans()
        user_plan = UserPlan(plan=plan, active=True, credit_card=credit_card)
        self.user_plans.append(user_plan)

    def _deactivate_plans(self):
        for user_plan in self.user_plans:
            user_plan.active = False

    def get_active_plan(self) -> Plan | None:
        for user_plan in self.user_plans:
            if user_plan.active:
                return user_plan.plan
        return None
```

**`User` virou o Aggregate Root do `subscription`**

A mudança de design: `User` deixou de ser um read model passivo e passou a ter comportamento de domínio. A regra "só um plano ativo por vez" vive dentro da entidade:

- `add_plan()` — porta de entrada para assinar um plano. Desativa os anteriores antes de ativar o novo.
- `_deactivate_plans()` — prefixo `_` indica método interno, não deve ser chamado de fora.

Ninguém de fora cria `UserPlan` diretamente — sempre passa por `user.add_plan(plan)`. Isso é o Aggregate Root em ação: **uma entrada, um controlador**.

**Por que `subscription` tem sua própria tabela `subscription.users`?**

Cada bounded context é dono dos seus dados. `subscription.users` tem apenas os campos relevantes para assinaturas — sem `hashed_password`, sem detalhes de autenticação. Se `authentication` mudar sua estrutura interna, `subscription` não é afetado.

**`user_plans = relationship("UserPlan", back_populates="user")`** usa string reference para evitar import circular — o SQLAlchemy resolve `"UserPlan"` no momento da configuração do mapper, não no import.

---

## Passo 26 — Entidade `UserPlan`: a assinatura

```
app/subscription/
├── plan/
│   └── _plan.py         ← catálogo de planos
└── user/
    ├── _user.py          ← Aggregate Root
    └── _user_plan.py     ← entidade interna: representa a assinatura  ← novo
```

**`app/subscription/user/_user_plan.py`:**
```python
from sqlalchemy import Column, ForeignKey, Integer
from app.subscription.user._user import User
from app.subscription.plan._plan import Plan
from app.infra.database import Base

class UserPlan(Base):
    __tablename__ = "user_plans"
    __table_args__ = {"schema": "subscription"}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    plan_id = Column(Integer, ForeignKey(Plan.id), nullable=False)
```

**`UserPlan` é uma entidade interna do agregado** — representa o fato de que um usuário assinou um plano. Ninguém de fora instancia `UserPlan` diretamente; isso é responsabilidade do Aggregate Root `User` via `add_plan()`.

| Campo | Papel |
|---|---|
| `user_id` | FK para `subscription.users.id` — dentro do mesmo bounded context |
| `plan_id` | FK para `subscription.plans.id` — dentro do mesmo bounded context |

`UserPlan` evoluído com campos de negócio e relacionamentos:

```python
class UserPlan(Base):
    __tablename__ = "user_plans"
    __table_args__ = {"schema": "subscription"}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("subscription.users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey(Plan.id), nullable=False)
    active = Column(Boolean, nullable=False, default=False)
    credit_card = Column(String(24), nullable=True)  # simplificado para estudo
    created_at = Column(DateTime, nullable=False)

    user = relationship("app.subscription.user._user.User", back_populates="user_plans")
    plan = relationship(Plan)
```

| Campo | Decisão |
|---|---|
| `active` | Flag explícita — uma assinatura pode existir mas estar inativa (cancelada, vencida) |
| `credit_card` | Simplificado para fins de estudo — em produção nunca se armazena o número; usa-se token do gateway de pagamento |
| `created_at` | Quando o usuário assinou |
| `relationship` | SQLAlchemy ORM — permite `user_plan.user` e `user_plan.plan` em vez de fazer JOIN manual |

**Por que string no `relationship("app.subscription.user._user.User")`?**

O SQLAlchemy aceita o caminho completo do módulo como string para evitar importação circular — `_user_plan.py` importa `_user.py` (para a FK), e `_user.py` importa `_user_plan.py` indiretamente via relationship. Usar a string adia a resolução para depois de todos os mappers estarem carregados.

**`plan = relationship(Plan)` sem `back_populates`** — `UserPlan` acessa `user_plan.plan`, mas `Plan` não precisa navegar de volta para `UserPlan` neste modelo. O `back_populates` é opcional quando a navegação é unidirecional.

**`__init__` sem validação de IDs — o Aggregate Root é o guardião:**
```python
def __init__(self, plan: Plan, active: bool, credit_card: str | None):
    self.plan = plan      # SQLAlchemy preenche plan_id via relationship
    self.active = active
    self.credit_card = credit_card
    self.created_at = datetime.now(timezone.utc)
```

`UserPlan` não valida `user_id` ou `plan_id` diretamente — esses valores são preenchidos pelo SQLAlchemy via relationship quando `user.user_plans.append(user_plan)` é chamado. A validação de negócio fica no Aggregate Root `User.add_plan()`, não aqui. `created_at` é sempre gerado internamente — timestamp automático no momento da assinatura.

---

---

## Passo 27 — Repositórios do módulo `subscription`

```
app/subscription/
├── plan/
│   ├── _plan.py
│   └── _plan_repository.py    ← novo
└── user/
    ├── _user.py
    ├── _user_plan.py
    └── _user_repository.py    ← novo
```

**`_plan_repository.py`:**
```python
class PlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, plan_id: int) -> Plan | None:
        return self.db.query(Plan).filter(Plan.id == plan_id).first()

def get_plan_repository(db: Session = Depends(get_db)) -> PlanRepository:
    return PlanRepository(db)
```

**`_user_repository.py`:**
```python
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user: User):
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)
```

**`create()` serve tanto para inserir quanto para atualizar.** Quando `user` já existe na sessão (carregado por `get_by_email`), o `db.add()` é um no-op — o SQLAlchemy já está rastreando o objeto. O `db.commit()` persiste todas as mudanças acumuladas na sessão: tanto as modificações nas entidades existentes (`active=False` nos UserPlans antigos) quanto a inserção do novo `UserPlan` adicionado ao `user.user_plans`.

O fluxo para assinar um plano:
```
caso de uso (select_plan)
  → user_repository.get_by_email(email)   # busca o Aggregate Root
  → plan_repository.get_by_id(plan_id)    # busca o plano
  → user.add_plan(plan, credit_card)      # regra de negócio no AR
  → user_repository.create(user)          # persiste o agregado inteiro
```

O repositório opera sempre no Aggregate Root (`User`) — nunca em `UserPlan` diretamente. Salvar o `User` propaga as mudanças em `user_plans` via SQLAlchemy (cascade).

---

---

## Passo 28 — Caso de uso: `_select_plan.py`

```
app/subscription/user/
├── _user.py              ← Aggregate Root
├── _user_plan.py         ← entidade interna
├── _user_repository.py   ← repositório
└── _select_plan.py       ← caso de uso: assinar plano  ← novo
```

**`app/subscription/user/_select_plan.py`:**
```python
class SelectPlanCreate(BaseModel):
    plan_id: int
    credit_card: str | None = None

async def select_plan(
    body: SelectPlanCreate,
    email: str = Depends(get_email_from_token),
    user_repository: UserRepository = Depends(get_user_repository),
    plan_repository: PlanRepository = Depends(get_plan_repository),
    query_user_by_email: QueryUserByEmail = Depends(get_query_user_by_email),
) -> None:
    user = user_repository.get_by_email(email)
    if not user:
        user_auth = query_user_by_email.execute(email)
        user = User(name=user_auth.name, email=email)

    plan = plan_repository.get_by_id(body.plan_id)
    user.add_plan(plan, body.credit_card)
    user_repository.create(user)
```

**Fluxo do caso de uso:**

```
POST /subscriptions/select-plan
  → extrai email do JWT (get_email_from_token)
  → busca User em subscription.users (ou cria via QueryUserByEmail)
  → busca Plan pelo id
  → user.add_plan(plan, credit_card)   ← regra de negócio no AR
  → user_repository.create(user)       ← persiste o agregado
```

**Decisões de design:**

| Elemento | Decisão |
|---|---|
| `email = Depends(get_email_from_token)` | Identidade vem do JWT — `subscription` não consulta `authentication` diretamente |
| `credit_card: str \| None = None` | Opcional no schema — a validação real fica em `User.add_plan()`: obrigatório só para planos pagos |
| `if not user: query_user_by_email.execute(email)` | Cria usuário no `subscription` com o nome real de `authentication` via Query Object — sem importar entidades externas |
| `user.add_plan(...)` | A regra de negócio fica no Aggregate Root — o caso de uso só orquestra |
| `user_repository.create(user)` | Funciona como upsert: insere se novo, propaga mudanças via cascade se existente |

---

---

## Passo 29 — Interface pública do módulo `subscription`

```
app/subscription/
├── __init__.py       ← exporta subscription_router
├── route.py          ← router público
├── plan/
└── user/
```

**`route.py`:**
```python
from fastapi import APIRouter
from app.subscription.user._select_plan import select_plan

subscription_router = APIRouter()

subscription_router.add_api_route(
    "/select-plan",
    endpoint=select_plan,
    methods=["POST"],
    tags=["subscription"],
    summary="Select a subscription plan for the user",
)
```

**`__init__.py`:**
```python
from .route import subscription_router

__all__ = ["subscription_router"]
```

**`main.py` atualizado — três módulos incluídos:**
```python
from app.authentication import user_router
from app.subscription import subscription_router
from app.movement import movement_router

app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(subscription_router, prefix="/subscriptions")
app.include_router(movement_router, prefix="/movements")
```

O `main.py` continua sendo um orquestrador puro — inclui os routers dos módulos sem conhecer nenhum detalhe interno. Cada bounded context expõe apenas seu router via `__init__.py`.

**Estrutura completa do monólito modular:**
```
track-money/app/
├── main.py                          ← orquestrador
├── domain_exception.py              ← compartilhado
├── infra/
│   └── database.py                  ← engine, sessão, init/create
├── authentication/                  ← bounded context
│   ├── __init__.py                  ← exporta user_router, get_email_from_token
│   ├── route.py
│   ├── get_email_from_token.py
│   ├── _user.py
│   ├── _user_repository.py
│   ├── _register_user.py
│   ├── _create_token.py
│   ├── _get_user_profile.py
│   ├── _auth.py
│   └── _password.py
└── subscription/                    ← bounded context
    ├── __init__.py                  ← exporta subscription_router
    ├── route.py
    ├── plan/
    │   ├── _plan.py
    │   └── _plan_repository.py
    └── user/
        ├── _user.py                 ← Aggregate Root
        ├── _user_plan.py
        ├── _user_repository.py
        └── _select_plan.py
```

---

---

## Passo 30 — Query Object: `QueryUserByEmail`

```
app/authentication/
├── query_user_by_email.py   ← público — query para outros módulos
└── __init__.py              ← exporta QueryUserByEmail + get_query_user_by_email
```

**`app/authentication/query_user_by_email.py`:**
```python
class UserByEmailResult:
    def __init__(self, id: int, name: str, email: str):
        self.id = id
        self.name = name
        self.email = email

class QueryUserByEmail:
    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(self, email: str) -> UserByEmailResult | None:
        user = self.user_repository.get_by_email(email)
        if not user:
            return None
        return UserByEmailResult(id=user.id, name=user.name, email=user.email)

def get_query_user_by_email(db: Session = Depends(get_db)) -> QueryUserByEmail:
    return QueryUserByEmail(db)
```

**`authentication/__init__.py` atualizado:**
```python
from .get_email_from_token import get_email_from_token
from .query_user_by_email import QueryUserByEmail, get_query_user_by_email
from .route import user_router

__all__ = ["user_router", "get_email_from_token", "QueryUserByEmail", "get_query_user_by_email"]
```

**Por que um Query Object e não usar o repositório diretamente?**

O `QueryUserByEmail` é um padrão CQRS (Command Query Responsibility Segregation) aplicado em escala pequena. Ele resolve um problema de fronteira entre bounded contexts:

- `subscription` precisa saber se um usuário existe em `authentication`
- Mas não pode importar `_UserRepository` (privado) nem a entidade `User` de `authentication`
- `QueryUserByEmail` é **público** e retorna um DTO (`UserByEmailResult`) com apenas os campos necessários — sem expor a entidade interna

| Sem Query Object | Com Query Object |
|---|---|
| `subscription` importa `_UserRepository` de `authentication` | `subscription` usa `QueryUserByEmail` da interface pública |
| Acoplamento direto com internals | Contrato explícito via DTO |
| Mudança interna em `authentication` quebra `subscription` | Mudança interna em `authentication` não afeta `subscription` |

---

## Passo 31 — Endpoint `GET /subscriptions/user` e `_plan.py` com `back_populates`

**`_get_user.py` — caso de uso: perfil do usuário com planos:**
```python
class PlanResponse(BaseModel):
    id: int
    name: str
    price: float
    active: bool
    is_free: bool

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    plans: list[PlanResponse] = []

async def get_user(
    email: str = Depends(get_email_from_token),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    user = user_repository.get_by_email(email)
    if not user:
        return None
    plans = [
        PlanResponse(id=up.plan.id, name=up.plan.name, price=up.plan.price,
                     active=up.active, is_free=up.plan.is_free)
        for up in user.user_plans
    ]
    return UserResponse(id=user.id, email=user.email, name=user.name, plans=plans)
```

**`_plan.py` — `back_populates` adicionado:**
```python
class Plan(Base):
    ...
    user_plans = relationship("UserPlan", back_populates="plan")
```

`Plan` agora declara o lado oposto do relacionamento — necessário para que `UserPlan.plan` funcione corretamente com `back_populates`.

**`route.py` atualizado — dois endpoints:**
```python
subscription_router.add_api_route("/select-plan", endpoint=select_plan, methods=["POST"], ...)
subscription_router.add_api_route("/user", endpoint=get_user, methods=["GET"], ...)
```

| Endpoint | Caso de uso | Auth |
|---|---|---|
| `POST /subscriptions/select-plan` | Assinar um plano | Sim |
| `GET /subscriptions/user` | Ver usuário e planos ativos | Sim |

**`_select_plan.py` atualizado — `QueryUserByEmail` injetado:**

```python
async def select_plan(
    body: SelectPlanCreate,
    email: str = Depends(get_email_from_token),
    user_repository: UserRepository = Depends(get_user_repository),
    plan_repository: PlanRepository = Depends(get_plan_repository),
    query_user_by_email: QueryUserByEmail = Depends(get_query_user_by_email),
) -> None:
    user = user_repository.get_by_email(email)
    if not user:
        user = User(name="Default", email=email)
    plan = plan_repository.get_by_id(body.plan_id)
    user.add_plan(plan, body.credit_card)
    user_repository.create(user)
```

`QueryUserByEmail` agora está em uso — quando o usuário não existe em `subscription.users`, consulta `authentication` para obter o nome real:

```python
user = user_repository.get_by_email(email)
if not user:
    user_auth = query_user_by_email.execute(email)   # cruza para authentication via Query Object
    user = User(name=user_auth.name, email=email)
```

Antes criava `User(name="Default", email=email)` — agora o nome vem do bounded context `authentication` via DTO, sem importar nenhuma entidade interna. Esse é o padrão Query Object em ação: `subscription` obtém dados de `authentication` sem acoplamento direto.

---

---

## Passo 32 — Query Object: `QueryUserPlan` no módulo `subscription`

```
app/subscription/
├── query_user_plan.py    ← público — expõe plano ativo para outros módulos
└── __init__.py           ← exporta subscription_router, QueryUserPlan, get_query_user_plan
```

**`subscription/query_user_plan.py`:**
```python
class UserPlanResult:
    def __init__(self, plan_id: int, plan_name: str, max_number_accounts: int):
        self.plan_id = plan_id
        self.plan_name = plan_name
        self.max_number_accounts = max_number_accounts

class QueryUserPlan:
    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def execute(self, email: str) -> UserPlanResult | None:
        result = self.user_repository.get_by_email(email)
        if not result:
            return None
        plan_active = result.get_active_plan()
        if not plan_active:
            return None
        return UserPlanResult(
            plan_id=plan_active.id,
            plan_name=plan_active.name,
            max_number_accounts=plan_active.max_number_accounts,
        )
```

`QueryUserPlan` expõe o plano ativo do usuário para outros módulos via DTO `UserPlanResult` — sem expor a entidade `User` ou `UserPlan` internamente. O campo `max_number_accounts` é a regra de negócio que o módulo `movement` vai usar para limitar contas bancárias.

---

## Passo 33 — Novo bounded context: `movement`

```
app/movement/
└── bank/
    ├── _bank_account.py           ← entidade + Value Object User
    ├── _bank_account_repository.py
    └── _register_bank_account.py  ← caso de uso
```

### Value Object: `User` em `movement`

**`_bank_account.py`:**
```python
class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email
        DomainException.validate(name and len(name) <= 128, "...")
        DomainException.validate(email and "@" in email and len(email) <= 128, "...")

    def __composite_values__(self):
        return self.name, self.email

class BankAccount(Base):
    __tablename__ = "bank_accounts"
    __table_args__ = {"schema": "movement"}

    id = Column(Integer, primary_key=True)
    name = Column(String(24), nullable=False)
    bank_name = Column(String(24), nullable=False)
    account_number = Column(String(24), nullable=False)
    balance = Column(Numeric(precision=15), nullable=False, default=0)
    status = Column(String(20), nullable=False, default=AccountStatus.ACTIVE.value)
    _user_name = Column("user_name", String(128), nullable=False)
    _user_email = Column("user_email", String(128), nullable=False)
    user = composite(User, _user_name, _user_email)
```

**`User` aqui é um Value Object**, não uma entidade:

| | Entidade | Value Object |
|---|---|---|
| Tem `id` | Sim | Não |
| Identidade por | `id` | valor dos atributos |
| Exemplo | `BankAccount`, `Plan` | `User` em `movement` |
| No banco | Tabela própria | Colunas embutidas na entidade dona |

`composite(User, _user_name, _user_email)` é o mecanismo do SQLAlchemy para embutir um Value Object — `user_name` e `user_email` são colunas em `movement.bank_accounts`, mas o Python enxerga como um objeto `User`. O `__composite_values__` diz ao SQLAlchemy como decompor o objeto em colunas.

**`AccountStatus` Enum** — estados possíveis de uma conta:
```python
class AccountStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"
    SUSPENDED = "suspended"
```

### Caso de uso: `_register_bank_account.py`

```python
async def register_bank_account(
    body: BankAccountCreate,
    email: str = Depends(get_email_from_token),
    bank_account_repository: BankAccountRepository = Depends(get_bank_account_repository),
    query_user_by_email: QueryUserByEmail = Depends(get_query_user_by_email),
    query_user_plan: QueryUserPlan = Depends(get_query_user_plan),
) -> None:
    # 1. verifica se tem plano ativo
    user_plan = query_user_plan.execute(email)
    if not user_plan:
        raise HTTPException(status_code=400, detail="User has no active plan")

    # 2. verifica limite de contas do plano
    bank_accounts = bank_account_repository.get_all_by_user(email)
    if len(bank_accounts) >= user_plan.max_number_accounts:
        raise HTTPException(status_code=400, detail="Maximum number of bank accounts reached")

    # 3. cria a conta com Value Object User
    user_auth = query_user_by_email.execute(email)
    user = User(name=user_auth.name, email=user_auth.email)
    bank_account = BankAccount(name=body.name, bank_name=body.bank_name,
                               account_number=body.account_number, user=user,
                               balance=body.initial_balance)
    bank_account_repository.create(bank_account)
```

**Comunicação cross-context via Query Objects:**

```
movement/bank
  → QueryUserPlan (subscription)   ← verifica plano e limite de contas
  → QueryUserByEmail (authentication) ← obtém nome do usuário
```

`movement` não importa nenhuma entidade de `subscription` ou `authentication` — só Query Objects da interface pública. Cada bounded context permanece autônomo.

---

## Passo 34 — Interface pública do módulo `movement`

```
app/movement/
├── __init__.py              ← exporta movement_router
├── route.py                 ← router público
└── bank/
    ├── __init__.py
    ├── _bank_account.py
    ├── _bank_account_repository.py
    └── _register_bank_account.py
```

**`app/movement/route.py`:**
```python
from fastapi import APIRouter
from app.movement.bank._register_bank_account import register_bank_account

movement_router = APIRouter()

movement_router.add_api_route(
    "/bank-accounts",
    endpoint=register_bank_account,
    methods=["POST"],
    response_model=None,
    tags=["movement"],
    summary="Register a new bank account for the user",
)
```

**`app/movement/__init__.py`:**
```python
from .route import movement_router

__all__ = ["movement_router"]
```

**`main.py` — três bounded contexts registrados:**
```python
from app.authentication import user_router
from app.subscription import subscription_router
from app.movement import movement_router

app.include_router(user_router, prefix="/users", tags=["users"])
app.include_router(subscription_router, prefix="/subscriptions")
app.include_router(movement_router, prefix="/movements")
```

O roteamento segue o mesmo padrão dos outros módulos — `main.py` só inclui routers, sem conhecer detalhes internos.

| Endpoint | Módulo | Auth |
|---|---|---|
| `POST /users/` | authentication | Não |
| `POST /users/token` | authentication | Não |
| `GET /users/profile` | authentication | Sim |
| `POST /subscriptions/select-plan` | subscription | Sim |
| `GET /subscriptions/user` | subscription | Sim |
| `POST /movements/bank-accounts` | movement | Sim |

**`database.py` — `init_database` com os três schemas:**
```python
def init_database():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS authentication"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS subscription"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS movement"))
        conn.commit()

def create_tables():
    engine = get_engine()
    from app.authentication._user import User          # noqa: F401
    from app.movement.bank._bank_account import BankAccount  # noqa: F401
    from app.subscription.plan._plan import Plan       # noqa: F401
    from app.subscription.user._user_plan import UserPlan  # noqa: F401
    Base.metadata.create_all(bind=engine)
```

`BankAccount` deve ser importado em `create_tables` — sem esse import, o SQLAlchemy não conhece a tabela `movement.bank_accounts` e o `create_all` não a cria.

---

## Passo 35 — Debug cross-context: rastreando o `plan_id` correto

**O bug:** ao trocar para o Basic Plan via `POST /subscriptions/select-plan`, o usuário continuava recebendo `400 - maximum bank accounts reached` ao tentar criar uma segunda conta.

**A investigação seguiu o caminho inverso dos bounded contexts:**

```
movement/_register_bank_account
  → QueryUserPlan.execute(email)   ← retorna max_number_accounts errado?
    → UserRepository.get_by_email
      → User.get_active_plan()
        → UserPlan.plan.max_number_accounts
```

**Comparação com o código do professor** não revelou diferenças funcionais — o código estava correto.

**Consulta direta ao banco revelou o problema:**
```
subscription.plans:
  id=2  → Free Plan    (max 1 conta,  price=0)
  id=3  → Basic Plan   (max 5 contas, price=9.90)
  id=4  → Premium Plan (max 15 contas, price=19.99)

subscription.user_plans para user_id=3:
  id=10 → plan_id=2 (Free Plan),  active=False
  id=11 → plan_id=2 (Free Plan),  active=True   ← chamada de select-plan não mudou o plano!
```

**A causa raiz:** o `endpoint.http` usava `plan_id: 2`, que é o **Free Plan** (máximo 1 conta) — não o Basic Plan. O usuário estava re-selecionando o mesmo Free Plan e por isso o limite continuava em 1.

```http
### ERRADO — plan_id 2 é o Free Plan
{
    "plan_id": 2,
    "credit_card": "1234 5678 9012 3456"
}

### CORRETO — plan_id 3 é o Basic Plan
{
    "plan_id": 3,
    "credit_card": "1234 5678 9012 3456"
}
```

**A lição:** os IDs de planos no banco de dados não são necessariamente sequenciais a partir de 1 — dependem de quando foram inseridos. Antes de testar fluxos que dependem de IDs, verificar os dados reais:

```sql
SELECT id, name, max_number_accounts, price FROM subscription.plans ORDER BY id;
```

**Por que o código estava correto mas o teste falhava?**

O monólito modular funcionou exatamente como projetado:
- `_deactivate_plans()` desativou o plano antigo
- `UserPlan` com `plan_id=2` foi criado ativo
- `QueryUserPlan` retornou corretamente `max_number_accounts=1` (do Free Plan)
- `movement` corretamente bloqueou a segunda conta

O bug era de dado de teste, não de código. A comparação com o código do professor confirmou isso — os arquivos eram idênticos. A consulta ao banco foi o que resolveu.

---

## Estrutura completa do monólito modular

```
track-money/app/
├── main.py                              ← orquestrador
├── domain_exception.py                  ← compartilhado
├── infra/
│   ├── __init__.py
│   └── database.py                      ← engine lazy, sessão, init/create (3 schemas)
├── authentication/                      ← bounded context
│   ├── __init__.py                      ← exporta: user_router, get_email_from_token,
│   │                                               QueryUserByEmail, get_query_user_by_email
│   ├── route.py                         ← POST /users, POST /users/token, GET /users/profile
│   ├── get_email_from_token.py          ← público: validação JWT para outros módulos
│   ├── query_user_by_email.py           ← público: Query Object cross-context
│   ├── _user.py                         ← entidade User (authentication.users)
│   ├── _user_repository.py              ← repositório (privado)
│   ├── _register_user.py                ← caso de uso: POST /users
│   ├── _create_token.py                 ← caso de uso: POST /users/token
│   ├── _get_user_profile.py             ← caso de uso: GET /users/profile
│   ├── _auth.py                         ← geração JWT (privado)
│   └── _password.py                     ← bcrypt (privado)
├── subscription/                        ← bounded context
│   ├── __init__.py                      ← exporta: subscription_router, QueryUserPlan,
│   │                                               get_query_user_plan
│   ├── route.py                         ← POST /select-plan, GET /user
│   ├── query_user_plan.py               ← público: Query Object cross-context
│   ├── plan/
│   │   ├── _plan.py                     ← entidade Plan (subscription.plans)
│   │   └── _plan_repository.py          ← repositório (privado)
│   └── user/
│       ├── __init__.py
│       ├── _user.py                     ← Aggregate Root User (subscription.users)
│       ├── _user_plan.py                ← entidade interna: assinatura
│       ├── _user_repository.py          ← repositório (privado)
│       ├── _select_plan.py              ← caso de uso: POST /select-plan
│       └── _get_user.py                 ← caso de uso: GET /user
└── movement/                            ← bounded context
    ├── __init__.py                      ← exporta: movement_router
    ├── route.py                         ← POST /bank-accounts
    └── bank/
        ├── __init__.py
        ├── _bank_account.py             ← entidade BankAccount + Value Object User
        ├── _bank_account_repository.py  ← repositório (privado)
        └── _register_bank_account.py    ← caso de uso: POST /bank-accounts
```

---

## Próximos passos

- [ ] Endpoints de listagem e remoção de contas bancárias
- [ ] Módulo de movimentações financeiras (entradas e saídas por conta)
- [ ] Testes automatizados por bounded context

---

*Atualizado em: 2026-04-22*
