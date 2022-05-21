import json
import re
import sys
from dataclasses import dataclass
from typing import Dict, List
import os

DESTINATION_DIRECTORY = "obsidian"


@dataclass
class OracleRoll:
    floor: int
    ceiling: int
    result: str
    summary: str = ""


@dataclass
class Oracle:
    name: str
    identifier: str
    description: str
    rolls: List[OracleRoll]

    @property
    def identifier_md(self):
        return (
            self.identifier.replace("/", "")
            .replace("_", "")
            .replace("StarforgedOracles", "")
        )


@dataclass
class OracleSection:
    name: str
    identifier: str
    oracles: List[Oracle]

    @property
    def identifier_md(self):
        return self.identifier.replace("/", "").replace("_", "")


def oracle_to_md(oracle: Oracle) -> str:
    """Format an oracle table in markdown."""
    result: List[str] = []
    result.append(f"## {oracle.name}")
    if oracle.description:
        result.append(f"_{oracle.description}_")
    result.append("")
    result.append(f"| dice: 1d100 | {oracle.name.replace(' ', '')} |")
    result.append(f"| :-: | - |")

    for roll in oracle.rolls:
        if roll.floor == roll.ceiling:
            dice_str = str(roll.floor)
        else:
            dice_str = f"{roll.floor} - {roll.ceiling}"
        result.append(f"| {dice_str} | {roll.result} |")
    result.append(f"^{oracle.identifier_md}")
    result.append("")
    return "\n".join(result)


def section_to_md(section: OracleSection) -> str:
    """Format a section of oracle tables in markdown."""
    result: List[str] = []
    result.append(f"# {section.name}")
    result.append("")
    for oracle in section.oracles:
        result.append(oracle_to_md(oracle))
    result.append("")
    result.append("")

    return "\n".join(result)


def section_to_roller_md(section: OracleSection) -> str:
    """Format a section of oracles in markdown, as a table of dice rollers."""
    result: List[str] = []
    result.append(f"## {section.name}")
    result.append("")
    result.append("|||")
    result.append("| - | -: |")
    tables_document = get_filename_oracle_tables(
        identifier=section.oracles[0].identifier
    ).replace(".md", "")
    for oracle in section.oracles:
        roller = f"`dice: [[{tables_document}#^{oracle.identifier_md}]]`"
        result.append(f"| {oracle.name} | {roller} |")
    result.append("")
    result.append("")

    return "\n".join(result)


def parse_roll_result(tables_document: str, result: str) -> str:
    """Parse a roll result and add the necessary dice rollers."""
    if "[" not in result:
        return result
    result = re.sub(
        r"\[\[⏵.*?\]\(.*?/Oracles/(.*?)\)\]",
        f"`dice: [[{tables_document}#^\1]]`",
        result,
    )
    result = re.sub(r"\[\[⏵(.*?)\].*?\)\]", r"\1", result)
    result = re.sub(r"\[⏵(.*?)\].*?\)", r"\1", result)
    result = re.sub(r"\[(.*?)\].*?\)", r"\1", result)
    result = result.replace("/", "")
    return result


def parse_oracle(data: Dict) -> Oracle:
    """Parse an oracle dict into an Oracle"""
    rolls: List[OracleRoll] = []
    if "Table" not in data:
        breakpoint()
    for row in data["Table"]:
        try:
            int(row["Floor"])
        except (ValueError, TypeError):
            continue
        tables_document = get_filename_oracle_tables(identifier=data["$id"]).replace(
            ".md", ""
        )
        result = parse_roll_result(
            tables_document=tables_document, result=row["Result"]
        )
        roll = OracleRoll(
            floor=row["Floor"],
            ceiling=row["Ceiling"],
            result=result,
            summary=row.get("Summary", ""),
        )
        rolls.append(roll)
    return Oracle(
        name=data["Name"],
        identifier=data["$id"],
        description=data.get("Description", ""),
        rolls=rolls,
    )


def parse_oracles(filename: str) -> List[OracleSection]:
    sections: List[OracleSection] = []
    with open(filename) as f:
        data = json.load(f)
    for section_data in data:
        oracles = []
        for oracle_data in section_data["Oracles"]:
            if "Table" in oracle_data:
                oracles.append(parse_oracle(oracle_data))
            elif "Oracles" in oracle_data:
                for sub_oracle in oracle_data["Oracles"]:
                    oracles.append(parse_oracle(sub_oracle))
            else:
                breakpoint()
        sections.append(
            OracleSection(
                name=section_data["Name"],
                oracles=oracles,
                identifier=section_data["$id"],
            )
        )
    return sections


def write_oracle_tables(filename: str, sections: List[OracleSection]):
    """Write oracle sections into the oracle tables file."""
    result: List[str] = []
    for section in sections:
        result.append(f"- [[#{section.name}]]")
        for oracle in section.oracles:
            result.append(f"  - [[#{oracle.name}]]")
    result.append("")
    for section in sections:
        result.append(section_to_md(section))
    with open(filename, "w") as f:
        f.write("\n".join(result))


def write_rollers(filename: str, sections: List[OracleSection]):
    """Write oracle sections into the oracle rollers file."""
    result: List[str] = []
    for section in sections:
        result.append(f"- [[#{section.name}]]")
    result.append("")
    for section in sections:
        result.append(section_to_roller_md(section))
    with open(filename, "w") as f:
        f.write("\n".join(result))


def get_filename_oracle_tables(identifier):
    name = identifier.split("/")[0]
    return f"{name}OracleTables.md"


def get_filename_oracle(identifier: str) -> str:
    """Return the filename on which an oracle should be stored.
    :param identifier: The identifier of an oracle (`Oracle.identifier`)
    """
    name = identifier.split("/")[0]
    return f"{name}Oracle.md"


def convert_oracles(filename: str) -> None:
    """Parse the json oracle file `filename` and write the oracles and rollers markdown files."""
    sections = parse_oracles(filename)
    identifier = sections[0].oracles[0].identifier
    filename_oracle_tables = os.path.join(
        DESTINATION_DIRECTORY, get_filename_oracle_tables(identifier=identifier)
    )
    filename_oracle = os.path.join(
        DESTINATION_DIRECTORY, get_filename_oracle(identifier=identifier)
    )
    write_oracle_tables(filename=filename_oracle_tables, sections=sections)
    write_rollers(filename=filename_oracle, sections=sections)
    print(f"Written {filename_oracle_tables} and {filename_oracle}")


if __name__ == "__main__":
    try:
        filename_input = sys.argv[1]
    except IndexError:
        print(f"Usage: python3 {sys.argv[0]} input_oracles.json")
        sys.exit(1)
    convert_oracles(filename_input)
