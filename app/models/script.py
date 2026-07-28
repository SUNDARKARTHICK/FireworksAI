"""Data models representing an educational lesson script.

This module contains only data structures. It performs no parsing,
no file I/O, and no validation. It exists solely to define the shape
of the data produced by the ingestion pipeline.
"""

from dataclasses import dataclass, field


@dataclass
class Section:
    """A single content section within a lesson.

    Attributes:
        heading: The title of the section.
        content: The body text belonging to the section.
    """

    heading: str
    content: str


@dataclass
class Metadata:
    """Descriptive metadata about a lesson, sourced from front matter.

    Attributes:
        title: The lesson's title.
        author: The lesson's author.
        language: The language the lesson is written in.
        category: The subject or topic category of the lesson.
        duration: The estimated duration of the lesson (e.g. "10 min").
        tags: A list of keywords describing the lesson.
    """

    title: str
    author: str
    language: str
    category: str
    duration: str
    tags: list[str] = field(default_factory=list)


@dataclass
class Script:
    """A complete, structured lesson ready for downstream processing.

    Attributes:
        metadata: Descriptive information about the lesson.
        introduction: The introductory text of the lesson.
        sections: An ordered list of the lesson's content sections.
        conclusion: The closing text of the lesson.
    """

    metadata: Metadata
    introduction: str
    sections: list[Section]
    conclusion: str
