from __future__ import annotations

import csv
import datetime as dt
import os
from dataclasses import dataclass
from typing import IO, Any, Callable, Literal, Self, cast, overload

from fpdf import FPDF


@dataclass
class Colloscope:
    colles: list[ColleData]
    holidays: list[dt.date]

    @property
    def groups(self) -> list[str]:
        """Get a unique list of available groups"""
        return list(set(c.group for c in self.colles))

    @classmethod
    def from_filename(cls, filename: str) -> Self:
        """
        Returns a list of all the collesDatas by reading a csv file.

        The csv file must follow the next syntaxe:
        ```csv
        Matiere,Prof,Jour,Heure,Salle,DD/MM/YY,DD/MM/YY,...,DD/MM/YY,Vacances,DD/MM/YY,...
        English,Mme Jane,Mercredi,12h,E12,3,5,1,,2
        ```

        The DD/MM/YY is the first Monday of the week. "Vacances" means a pause for holidays.

        The numbers behind the classroom are the groups identifiers. They will be handled as string, as they can be anything in practice
        """
        colles: list[ColleData] = []

        with open(filename, encoding="utf-8", errors="ignore") as f:
            csv_reader = csv.reader(f, delimiter=",")

            holidays: list[dt.date] = []
            header = next(csv_reader)

            """
            | headers
            | colle slot 1
            | colle slot 2
            | ...
            v
            """
            for row in csv_reader:
                # subject,professor,weekday,hour,classroom,[groups...]
                subject, professor, week_day, raw_hour, classroom = row[0:5]
                raw_hour, raw_minute = raw_hour.split("h")  # raw hour pattern: xxhyy
                hour: dt.time = dt.time(hour=int(raw_hour), minute=int(raw_minute) if raw_minute else 0)

                for x in range(5, len(row)):
                    # [5],group,group,group,...
                    group = row[x]
                    week = dt.datetime.strptime(header[x], "%d/%m/%y")
                    date: dt.date = day_offset(week, week_day)

                    if group != "":
                        colles.append(ColleData(group, subject, professor, date, week_day, hour, classroom))

        for i, week in enumerate(header):
            if week.lower() == "vacances":
                if not header[i - 1]:
                    continue
                week = dt.datetime.strptime(header[i - 1], "%d/%m/%y")
                holidays.append(week + dt.timedelta(days=7))

        return cls(colles, holidays)


@dataclass
class ColleData:
    group: str
    subject: str
    professor: str
    date: dt.date
    week_day: str
    time: dt.time
    classroom: str

    def __post_init__(self):
        self.week_day = self.week_day.lower()

    def __str__(self):
        return f"Le {self.str_date}, passe le groupe {self.group} en {self.classroom} avec {self.professor} à {self.str_time}"

    @property
    def str_date(self) -> str:
        return self.date.strftime("%d/%m/%Y")

    @property
    def str_time(self) -> str:
        return self.time.strftime("%hh%m")

    @property
    def long_str_date(self) -> str:
        """
        Return the date in a human readable format :
        Ex: "Lundi 10 janvier"
        """
        monthName = [
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        ]

        return f"{self.week_day} {self.date.day} {monthName[self.date.month - 1]}"


def day_offset(week: dt.date, week_day: str) -> dt.date:
    week_days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]

    delta = dt.timedelta(days=week_days.index(week_day))
    return week + delta


def sort_colles(
    colles_datas: list[ColleData], sort_type: Literal["temps", "prof", "groupe"] = "temps"
) -> list[ColleData]:
    key: Callable[[ColleData], Any]
    match sort_type:
        case "temps":
            key = lambda c: c.date
        case "prof":
            key = lambda c: c.professor
        case "groupe":
            key = lambda c: c.group
    return sorted(colles_datas, key=key)


def agenda_format_time(time: dt.time) -> str:
    return time.strftime("%I:%M %p")


def add_one_hour(time: dt.time) -> str:
    """Ajoute une heure à l'heure donnée (pas de colle a minuit donc pas besoin de gérer 23h + 1h)"""
    return agenda_format_time(dt.time(hour=time.hour + 1, minute=time.minute))


@overload
def write_colles(
    file: IO[str],
    export_type: Literal["csv", "agenda", "todoist"],
    colles_datas: list[ColleData],
    group: str,
    holidays: list[dt.date],
) -> None:
    ...


@overload
def write_colles(
    file: IO[bytes],
    export_type: Literal["pdf"],
    colles_datas: list[ColleData],
    group: str,
    holidays: list[dt.date],
) -> None:
    ...


def write_colles(
    file: IO[str] | IO[bytes],
    export_type: Literal["pdf", "csv", "agenda", "todoist"],
    colles_datas: list[ColleData],
    group: str,
    holidays: list[dt.date],
):
    export_path = f"./groupe{group}"

    if os.path.exists(export_path) == False:
        os.mkdir(export_path)

    def csv_method(f: IO[str]):
        # write the sorted data into a csv file
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["date", "heure", "prof", "salle", "matière"])

        for colle in colles_datas:
            data = [colle.str_date, colle.time, colle.professor, colle.classroom, colle.subject]
            writer.writerow(data)

    def agenda_method(f: IO[str]):
        agenda: list[dict[str, Any]] = []
        for colle in colles_datas:
            agenda.append(
                {
                    "Subject": f"{colle.subject} {colle.professor} {colle.classroom}",
                    "Start Date": colle.str_date,
                    "Start Time": agenda_format_time(colle.time),
                    "End Date": colle.str_date,
                    "End Time": add_one_hour(colle.time),
                    "All Day Event": False,
                    "Description": f"Colle de {colle.subject} avec {colle.professor} en {colle.classroom} a {colle.time}",
                    "Location": colle.classroom,
                }
            )

        fieldnames = [
            "Subject",
            "Start Date",
            "Start Time",
            "End Date",
            "End Time",
            "All Day Event",
            "Description",
            "Location",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for colle in agenda:
            writer.writerow(colle)

    def todoist_method(f: IO[str]):
        type, priority = "task", 2
        todoist: list[dict[str, Any]] = []
        for colle in colles_datas:
            todoist.append(
                {
                    "TYPE": type,
                    "CONTENT": f"Colle de {colle.subject} avec {colle.professor}",
                    "DESCRIPTION": f"Salle {colle.classroom}",
                    "PRIORITY": priority,
                    "INDENT": "",
                    "AUTHOR": "",
                    "RESPONSIBLE": "",
                    "DATE": f"{colle.str_date} {colle.str_time}",
                    "DATE_LANG": "fr",
                    "TIMEZONE": "Europe/Paris",
                }
            )

        fieldnames = [
            "TYPE",
            "CONTENT",
            "DESCRIPTION",
            "PRIORITY",
            "INDENT",
            "AUTHOR",
            "RESPONSIBLE",
            "DATE",
            "DATE_LANG",
            "TIMEZONE",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for colle in todoist:
            writer.writerow(colle)

    def pdf_method(f: IO[bytes]):
        vacanceIndex = 0
        pdf = FPDF()
        pdf.add_font("Arial", "", "./resources/fonts/arial.ttf")
        pdf.add_font("Arial", "B", "./resources/fonts/arial_bold.ttf")
        pdf.add_page()
        page_width = pdf.w - 2 * pdf.l_margin

        pdf.set_font("Arial", "U", 14)
        pdf.cell(page_width, 0.0, f"Colloscope groupe {group}", align="C")
        pdf.ln(10)

        pdf.set_font("Arial", "", 11)

        col_width = page_width / 4

        pdf.ln(1)

        th = pdf.font_size + 2

        pdf.set_font("Arial", "B", 11)
        pdf.cell(10, th, text="Id", border=1, align="C")  # type: ignore
        pdf.cell(40, th, "Date", border=1, align="C")
        pdf.cell(20, th, "Heure", border=1, align="C")
        pdf.cell(col_width * 0.75, th, "Prof", border=1, align="C")
        pdf.cell(30, th, "Salle", border=1, align="C")
        pdf.cell(col_width, th, "Matiere", border=1, align="C")
        pdf.set_font("Arial", "", 11)
        pdf.ln(th)

        for i, colle in enumerate(colles_datas, 1):
            if vacanceIndex < len(holidays):  # fait un saut de ligne à chaque vacances
                if colle.date > holidays[vacanceIndex]:
                    pdf.ln(th * 0.5)
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(90 + 2 * col_width, th, f"Vacances", align="C")
                    pdf.set_font("Arial", "", 11)
                    pdf.ln(th * 1.5)
                    vacanceIndex += 1
            pdf.cell(10, th, str(i), border=1, align="C")
            pdf.set_font("Arial", "", 9)
            pdf.cell(40, th, colle.long_str_date, border=1, align="C")
            pdf.set_font("Arial", "", 11)
            pdf.cell(20, th, colle.str_time, border=1, align="C")
            pdf.cell(col_width * 0.75, th, colle.professor, border=1, align="C")
            pdf.cell(30, th, colle.classroom, border=1, align="C")
            pdf.cell(col_width, th, colle.subject, border=1, align="C")
            pdf.ln(th)

        pdf.ln(10)

        pdf.set_font("Times", "", 10)
        pdf.output(f)  # type: ignore

    match export_type:
        case "csv":
            file = cast(IO[str], file)
            return csv_method(file)
        case "agenda":
            file = cast(IO[str], file)
            return agenda_method(file)
        case "pdf":
            file = cast(IO[bytes], file)
            return pdf_method(file)
        case "todoist":
            file = cast(IO[str], file)
            return todoist_method(file)


def get_group_upcoming_colles(colles: list[ColleData], group: str) -> list[ColleData]:
    colles = sort_colles(colles, sort_type="temps")  # sort by time
    today = dt.date.today() + dt.timedelta(days=-1)  # date de la veille

    filtered_colles = [c for c in colles if c.group == group and c.date >= today]
    return filtered_colles
