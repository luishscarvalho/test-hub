from threading import Lock

from target_api.modelos import Tarefa, TarefaEntrada

# Estado inicial fixo: a API sempre sobe igual (ADR-008).
SEED: tuple[TarefaEntrada, ...] = (
    TarefaEntrada(titulo="Ler a spec OpenAPI", concluida=True),
    TarefaEntrada(titulo="Gerar os smoke tests", concluida=False),
    TarefaEntrada(titulo="Consultar o histórico de runs", concluida=False),
)


class RepositorioDeTarefas:
    """Tarefas em memória. As rotas síncronas rodam em threads, por isso o lock."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._tarefas: dict[int, Tarefa] = {}
        self._proximo_id = 1
        for entrada in SEED:
            self.criar(entrada)

    def listar(self) -> list[Tarefa]:
        with self._lock:
            return list(self._tarefas.values())

    def buscar(self, id: int) -> Tarefa | None:
        with self._lock:
            return self._tarefas.get(id)

    def criar(self, entrada: TarefaEntrada) -> Tarefa:
        with self._lock:
            tarefa = Tarefa(id=self._proximo_id, **entrada.model_dump())
            self._tarefas[tarefa.id] = tarefa
            self._proximo_id += 1
            return tarefa

    def editar(self, id: int, entrada: TarefaEntrada) -> Tarefa | None:
        with self._lock:
            if id not in self._tarefas:
                return None
            tarefa = Tarefa(id=id, **entrada.model_dump())
            self._tarefas[id] = tarefa
            return tarefa

    def apagar(self, id: int) -> bool:
        with self._lock:
            return self._tarefas.pop(id, None) is not None
