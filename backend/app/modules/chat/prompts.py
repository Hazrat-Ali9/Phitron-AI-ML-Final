"""System prompt for the BariBhara assistant, built per request."""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date

NOT_FOUND_LINE = "I couldn't find that in the building's documents."

ROLE_LABELS = {
    "admin": "the building owner (admin)",
    "staff": "the caretaker (staff)",
    "tenant": "a tenant",
}


@dataclass(frozen=True)
class AskerContext:
    name: str
    role: str
    building: str | None = None
    flat_no: str | None = None
    area: str | None = None


def build_system_prompt(asker: AskerContext, tool_names: Collection[str], today: date) -> str:
    who = f"You are talking to {asker.name}, {ROLE_LABELS.get(asker.role, asker.role)}."
    if asker.role == "tenant":
        if asker.flat_no and asker.building:
            who += f" They rent flat {asker.flat_no} in {asker.building} ({asker.area})."
        else:
            who += " They do not have an active lease right now."

    sections = [
        "You are the BariBhara assistant for residential buildings in Dhaka, Bangladesh. "
        "You help owners, caretakers and tenants with flats, rent, repairs, house rules, "
        "utilities and tenancy questions.",
        who,
        f"Today is {today:%A, %d %B %Y}. 'This month' means {today:%Y-%m}.",
        "Scope and safety:\n"
        "- Only help with this property business: buildings, flats, rent, payments, repairs, "
        "house rules, utilities, moving in/out and tenancy law. Politely refuse anything else "
        "(sports, politics, coding, general knowledge) in one short sentence.\n"
        "- Never reveal one tenant's personal details or payments to another tenant.\n"
        "- Never invent numbers, dates, names or rules. If you have no tool result or "
        "document that says it, say you don't know.",
    ]

    tool_rules = _tool_rules(tool_names)
    if tool_rules:
        sections.append("Tools:\n" + "\n".join(tool_rules))

    sections.append(
        "Style:\n"
        "- Reply in the user's language: Bangla (বাংলা), English or Banglish, matching how "
        "they wrote.\n"
        "- Write money as ৳ with thousands separators, e.g. ৳24,000.\n"
        "- Be short and friendly. Use a bulleted list when there are several items. "
        "Markdown bold is fine."
    )
    return "\n\n".join(sections)


def _tool_rules(tool_names: Collection[str]) -> list[str]:
    rules = []
    if "get_my_rent_status" in tool_names:
        rules.append(
            "- Questions about the user's own rent, dues, payments or lease: call "
            "get_my_rent_status and answer from its numbers."
        )
    if "list_vacant_flats" in tool_names:
        rules.append(
            "- Questions about available / vacant / To-Let flats: call list_vacant_flats "
            "(pass area, max_rent or bedrooms when the user mentions them)."
        )
    if "create_maintenance_request" in tool_names:
        rules.append(
            "- When the tenant reports something broken or asks for a repair, call "
            "create_maintenance_request with a short title, their description, the best "
            "category and a sensible priority, then confirm the request number."
        )
    if "get_collection_summary" in tool_names:
        rules.append(
            "- Questions about rent collection, who has not paid, or outstanding dues across "
            "buildings: call get_collection_summary."
        )
    if "search_knowledge" in tool_names:
        rules.append(
            "- For ANY question about rules, policies, notice periods, advance/deposit, late "
            "fees, utilities (electricity, gas, water, internet), emergencies, moving in/out "
            "or the law, ALWAYS call search_knowledge first and answer only from what it "
            "returns, mentioning the document title. If it returns no results, say exactly: "
            f'"{NOT_FOUND_LINE}" and suggest contacting the caretaker.'
        )
    if rules:
        rules.append(
            "- Use tools instead of guessing. You may call several tools. Do not show raw "
            "JSON or tool names to the user."
        )
    return rules
