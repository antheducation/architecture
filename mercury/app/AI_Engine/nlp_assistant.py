"""Assistant conversationnel (livrables #04 et #20).

Analyse deterministe par patrons : aucun appel reseau, latence negligeable,
comportement previsible. Un adaptateur LLM peut la remplacer, mais il ne
peut emettre qu'une commande du meme schema, validee ensuite : c'est ce
qui garantit qu'aucune hallucination ne corrompt le projet.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

STYLES = ("moderne", "luxe", "classique", "industriel", "scandinave",
          "minimaliste", "arabe", "japonais", "africain", "contemporain")
TYPES = ("maison", "villa", "appartement", "bureau", "restaurant", "hotel",
         "magasin", "entrepot", "clinique", "ecole")


@dataclass
class Command:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    utterance: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {"action": self.action, "params": self.params,
                "confiance": self.confidence}


class LanguageModel(Protocol):
    """Contrat d'un LLM : il ne rend qu'une commande, jamais un projet."""

    def complete(self, system: str, user: str) -> Dict[str, Any]:
        ...


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return text.lower().strip()


class ConversationalAssistant:
    """Traduit une phrase en commande typee, puis l'execute."""

    PATTERNS = [
        (r"(change|passe|mets?|applique).*(style|deco\w*)\s+(en\s+)?(?P<style>\w+)",
         "set_style"),
        (r"style\s+(?P<style>\w+)", "set_style"),
        (r"(ajoute|mets?|place)\s+(?P<n>\d+)\s+(places?|couverts?|sieges?)",
         "set_seats"),
        (r"(agrandis|augmente)\s+(la\s+|le\s+)?(?P<room>[\w' -]+?)"
         r"(\s+de\s+(?P<pct>\d+)\s*%)?$", "resize_room"),
        (r"(reduis|diminue)\s+(la\s+|le\s+)?(?P<room>[\w' -]+?)"
         r"(\s+de\s+(?P<pct>\d+)\s*%)?$", "shrink_room"),
        (r"(transforme|convertis|change).*(en)\s+(?P<type>[\w -]+)$",
         "set_building_type"),
        # L'alternation doit tester "une" avant "un", sinon "une maison"
        # laisse un "e" orphelin qui devient le type detecte.
        (r"(genere|cree|dessine)\s+(?:une?\s+)?(?P<type>[a-z]+)"
         r"(?:\s+de\s+(?P<surface>\d+)\s*m2?)?", "generate"),
        (r"(genere|calcule|fais)\s+(le\s+)?(devis|estimation|metre|budget)",
         "estimate"),
        (r"(exporte?)\s+(en\s+)?(?P<fmt>ifc|obj|gltf|dxf|svg|json)", "export"),
        (r"\b(aide|help|commandes)\b", "help"),
    ]

    def __init__(self, llm: Optional[LanguageModel] = None) -> None:
        self.llm = llm
        self.handlers: Dict[str, Callable[..., Any]] = {}
        self.history: List[Command] = []

    def register(self, action: str, handler: Callable[..., Any]) -> None:
        """Branche l'execution d'une action. Sans handler, la commande est rendue."""
        self.handlers[action] = handler

    def parse(self, text: str) -> Command:
        normalized = _normalize(text)
        for pattern, action in self.PATTERNS:
            match = re.search(pattern, normalized)
            if not match:
                continue
            groups = {k: v for k, v in match.groupdict().items() if v}
            params: Dict[str, Any] = {}
            confidence = 0.9
            if action == "set_style":
                style = groups.get("style", "")
                if style not in STYLES:
                    continue
                params["style"] = style
                confidence = 0.95
            elif action == "set_seats":
                params["count"] = int(groups["n"])
            elif action in ("resize_room", "shrink_room"):
                params["room"] = groups.get("room", "").strip()
                percent = int(groups.get("pct", 20))
                params["percent"] = -percent if action == "shrink_room" else percent
                action = "resize_room"
            elif action in ("set_building_type", "generate"):
                raw = groups.get("type", "")
                found = next((t for t in TYPES if t in raw), None)
                if not found:
                    continue
                params["type"] = found
                if groups.get("surface"):
                    params["surface"] = float(groups["surface"])
            elif action == "export":
                params["format"] = groups["fmt"]
            command = Command(action, params, confidence, text)
            self.history.append(command)
            return command

        if self.llm is not None:
            try:
                raw = self.llm.complete(
                    "Convertis la demande en une commande JSON.", text)
                action = str(raw.get("action", "unknown"))
                if action != "unknown":
                    command = Command(action, dict(raw.get("params", {})), 0.8, text)
                    self.history.append(command)
                    return command
            except Exception:
                pass

        command = Command("unknown", {"text": text}, 0.0, text)
        self.history.append(command)
        return command

    def execute(self, text: str, *args, **kwargs) -> Dict[str, Any]:
        command = self.parse(text)
        handler = self.handlers.get(command.action)
        if handler is None:
            return {
                "commande": command.as_dict(),
                "execute": False,
                "message": "Commande non comprise. Exemples : "
                           "« genere une maison de 110 m2 », "
                           "« change le style en moderne », "
                           "« exporte en ifc ».",
            }
        try:
            result = handler(command.params, *args, **kwargs)
            return {"commande": command.as_dict(), "execute": True,
                    "resultat": result}
        except Exception as error:
            return {"commande": command.as_dict(), "execute": False,
                    "message": "Echec : %s" % error}
