"""Demo mode: replay pre-generated examples with no network and no API key."""
from pathlib import Path

from src.models import Language, PipelineResult

DEFAULT_EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

DEMO_CASES: dict[str, dict[Language, str]] = {
    "referral": {
        "en": "Referral program: let existing customers invite friends by link and reward both sides with a discount on their next order.",
        "pt-BR": "Programa de indicação: permitir que clientes atuais convidem amigos por link e que ambos ganhem desconto no próximo pedido.",
    },
    "abandoned_cart": {
        "en": "Abandoned cart recovery: remind shoppers who left items in their cart with a timely email and an easy way back to checkout.",
        "pt-BR": "Recuperação de carrinho abandonado: lembrar compradores que deixaram itens no carrinho com um e-mail no momento certo e um caminho fácil de volta ao checkout.",
    },
}


def load_demo(case_id: str, language: Language,
              examples_dir: Path = DEFAULT_EXAMPLES_DIR) -> PipelineResult:
    if case_id not in DEMO_CASES:
        raise KeyError(f"Unknown demo case: {case_id}")
    path = examples_dir / f"{case_id}.{language}.json"
    return PipelineResult.model_validate_json(path.read_text(encoding="utf-8"))
