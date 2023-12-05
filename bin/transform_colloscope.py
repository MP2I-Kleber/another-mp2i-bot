import csv
from enum import Enum

import typer


class Version(Enum):
    MPI = "MPI"
    MP2I = "MP2I"


def main(input: str, output: str, version: Version):
    with open(input, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=";")
        lines = list(reader)

    if version == Version.MPI:
        new_lines = transform_mpi(lines)
    elif version == Version.MP2I:
        new_lines = lines

    with open(output, "w", newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=",")
        writer.writerows(new_lines)


def transform_mpi(lines: list[list[str]]):
    lines = lines[3:]
    header, lines = lines[0], lines[2:]
    new_header: list[str] = [""] * 5
    for i, column in enumerate(header):
        if i < 5:
            continue
        date_parts = column.split("-")
        date_parts[2] = date_parts[2][2:]
        new_header.append("/".join(date_parts))

    # headers must be:
    # subject, professor, weekday, hour, classroom

    # headers are:
    # subject, professor, classroom, weekday, hour
    for i, line in enumerate(lines):
        line[2], line[3], line[4] = line[3], line[4], line[2]
        line[3] = line[3].split("-")[0].replace(" ", "")
        if not any(line):
            lines = lines[:i]
            break

    lines.insert(0, new_header)
    return lines


if __name__ == "__main__":
    typer.run(main)
