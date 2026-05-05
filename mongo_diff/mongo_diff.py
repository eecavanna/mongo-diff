from difflib import unified_diff
from types import SimpleNamespace
from typing import Any, Iterator, Optional

import dictdiffer
import typer
from typing_extensions import Annotated
from pymongo.collection import Collection
from pymongo import MongoClient, timeout
from bson import json_util
from rich.console import Console
from rich.markup import escape
from rich.table import Table, Column
from rich.progress import Progress
from rich.text import Text
from rich import box

app = typer.Typer(
    help="Compare two MongoDB collections.",
    add_completion=False,  # hides the shell completion options from `--help` output
)


class Result:
    r"""The result of the comparison."""

    def __init__(self, num_documents_in_collection_a: int, num_documents_in_collection_b: int) -> None:
        r"""Initializes the result."""
        self.num_documents_in_collection_a: int = num_documents_in_collection_a
        self.num_documents_in_collection_b: int = num_documents_in_collection_b
        self.identifiers_of_documents_in_collection_a_only: list[Any] = []
        self.identifiers_of_documents_in_collection_b_only: list[Any] = []
        self.identifiers_of_differing_documents: list[Any] = []
        self.diff_lines_of_differing_documents: dict[Any, list[str]] = {}
    
    @property
    def num_documents_in_collection_a_only(self) -> int:
        return len(self.identifiers_of_documents_in_collection_a_only)
    
    @property
    def num_documents_in_collection_b_only(self) -> int:
        return len(self.identifiers_of_documents_in_collection_b_only)
    
    @property
    def num_differing_documents(self) -> int:
        return len(self.identifiers_of_differing_documents)

    @staticmethod
    def colorize_if(raw_string: str, condition: bool, color: str) -> str:
        r"""Surrounds the raw string with Rich color tags if the condition is true."""
        return f"[{color}]{raw_string}[/{color}]" if condition else raw_string

    @staticmethod
    def colorize_diff_lines(diff_lines: list[str]) -> list[Text]:
        r"""
        Returns a list of Rich `Text` instances corresponding to the diff lines, with colorization.
        The caller can then display those `Text` instances via plain `console.print()` calls.

        References:
        - https://rich.readthedocs.io/en/latest/text.html
        - https://rich.readthedocs.io/en/latest/protocol.html
        """

        colorized_lines: list[Text] = []
        for line in diff_lines:
            if line.startswith("-"):
                colorized_lines.append(Text(line, style="red"))
            elif line.startswith("+"):
                colorized_lines.append(Text(line, style="green"))
            else:
                colorized_lines.append(Text(line))
        return colorized_lines

    def get_all_colorized_diff_lines(self) -> list[Text]:
        r"""
        Returns a list of Rich `Text` instances that, together, represent the diffs of all differing
        documents, with colorization.
        """

        colorized_lines: list[Text] = []
        for diff_lines in self.diff_lines_of_differing_documents.values():
            colorized_lines_part = self.colorize_diff_lines(diff_lines=diff_lines)
            colorized_lines.extend(colorized_lines_part)
            colorized_lines.append(Text(""))
        return colorized_lines

    def get_summary_table(self, title: Optional[str] = "Result") -> Table:
        r"""
        Returns a Rich Table summarizing the result.

        Reference: https://rich.readthedocs.io/en/stable/tables.html
        """
        table = Table(Column(header="Description"), Column(header="Quantity", justify="right"),
                      title=title,
                      box=box.ROUNDED,
                      highlight=True)
        table.add_row("Documents in collection A",
                      str(self.num_documents_in_collection_a))
        table.add_row("Documents in collection B",
                      str(self.num_documents_in_collection_b))
        table.add_section()
        table.add_row("Documents in collection A [bold]only[/bold]",
                      self.colorize_if(raw_string=str(self.num_documents_in_collection_a_only),
                                       condition=self.num_documents_in_collection_a_only > 0,
                                       color="red"))
        table.add_row("Documents in collection B [bold]only[/bold]",
                      self.colorize_if(raw_string=str(self.num_documents_in_collection_b_only),
                                       condition=self.num_documents_in_collection_b_only > 0,
                                       color="red"))
        table.add_section()
        table.add_row("Documents that differ between collections",
                      self.colorize_if(raw_string=str(self.num_differing_documents),
                                       condition=self.num_differing_documents > 0,
                                       color="red"))
        return table


class Comparator():
    """Compares MongoDB collections with one another."""

    def __init__(self, console: Console | None = None) -> None:
        """
        Initializes the comparator with the Rich `Console` instance, if any, onto which you want the
        comparator to print progress messages.
        """

        if isinstance(console, Console):
            self.console = console
        else:
            # Use a placeholder class whose `print` method does nothing.
            # Docs: https://docs.python.org/3/library/types.html#types.SimpleNamespace
            self.console = SimpleNamespace(print=lambda *args, **kwargs: None)

    @staticmethod
    def compare_documents(document_a: dict, document_b: dict, ignore_oid: bool = False) -> bool:
        r"""
        Returns `True` if the documents have the same fields and values as one another;
        otherwise `False`. Considers the `_id` field unless you opt out via `ignore_oid`.

        >>> Comparator.compare_documents({"a": 1}, {"a": 1})
        True
        >>> Comparator.compare_documents({"_id": 1, "a": 1}, {"_id": 2, "a": 1})
        False
        >>> Comparator.compare_documents({"_id": 1, "a": 1}, {"_id": 2, "a": 1}, ignore_oid=True)
        True
        """

        fields_to_ignore = {"_id"} if ignore_oid else set()
        differences_generator = dictdiffer.diff(document_a, document_b, ignore=fields_to_ignore)

        # Check whether the generator (which is an iterator) yields any differences.
        documents_are_same = False
        try:
            # Note: If this statement causes a `StopIteration` to be raised, it means the generator
            #       does not have any differences to yield (i.e. the documents match one another).
            _ = next(differences_generator)
        except StopIteration:
            documents_are_same = True
        return documents_are_same

    @staticmethod
    def generate_diff(
        document_a: dict,
        document_b: dict,
        label_a: str,
        label_b: str,
        ignore_oid: bool = False,
    ) -> Iterator[str]:
        r"""
        Returns an iterator that yields the lines of a Git-like diff of the documents' canonical
        JSON representations. Considers the `_id` field unless you opt out via `ignore_oid`.

        Reference: https://pymongo.readthedocs.io/en/stable/api/bson/json_util.html

        >>> document_a = dict(_id=1, id="123", name="adam")
        >>> document_b = dict(_id=2, id="123", name="betty")
        >>> document_c = dict(_id=1, id="123", name="betty")
        >>> for line in list(Comparator.generate_diff(document_a, document_b, "left", "right")):
        ...     print(line)
        --- left
        +++ right
        @@ -1,7 +1,7 @@
         {
           "_id": {
        -    "$numberInt": "1"
        +    "$numberInt": "2"
           },
           "id": "123",
        -  "name": "adam"
        +  "name": "betty"
         }
        >>> for line in list(Comparator.generate_diff(document_a, document_b, "left", "right", ignore_oid=True)):
        ...     print(line)
        --- left
        +++ right
        @@ -1,4 +1,4 @@
         {
           "id": "123",
        -  "name": "adam"
        +  "name": "betty"
         }
        >>> for line in list(Comparator.generate_diff(document_b, document_c, "left", "right")):
        ...     print(line)
        --- left
        +++ right
        @@ -1,6 +1,6 @@
         {
           "_id": {
        -    "$numberInt": "2"
        +    "$numberInt": "1"
           },
           "id": "123",
           "name": "betty"
        >>> list(Comparator.generate_diff(document_b, document_c, "left", "right", ignore_oid=True))
        []
        """

        candidate_a = document_a.copy()
        candidate_b = document_b.copy()
        if ignore_oid:
            candidate_a.pop("_id", None)
            candidate_b.pop("_id", None)

        a_json = json_util.dumps(
            candidate_a,
            json_options=json_util.CANONICAL_JSON_OPTIONS,
            indent=2,
            sort_keys=True,
        )
        b_json = json_util.dumps(
            candidate_b,
            json_options=json_util.CANONICAL_JSON_OPTIONS,
            indent=2,
            sort_keys=True,
        )
        diff_lines = unified_diff(
            a_json.splitlines(),
            b_json.splitlines(),
            fromfile=label_a,
            tofile=label_b,
            lineterm="",
        )
        return diff_lines

    def compare_collections(
        self,
        collection_a: Collection,
        collection_b: Collection,
        identifier_field_name_a: str,
        identifier_field_name_b: str,
        ignore_oid: bool,
    ) -> Result:
        """
        Compares one MongoDB collection with another one.

        Identifies documents that (based on their identifier field) exist in one collection and not
        in the other collection. Also identifies differences that exist between documents that
        (based on their identifier field) exist in both collections, but do not match one another.

        :param collection_a: One collection.
        :param collection_b: The other collection.
        :param identifier_field_name_a: The name of the field of each document in collection A to
                                        use to identify a corresponding document in collection B.
        :param identifier_field_name_b: The name of the field of each document in collection B to
                                        use to identify a corresponding document in collection A.
        :param ignore_oid: Whether to ignore the `_id` field when comparing documents.

        :returns: A `Result` instance containing the result of the comparison.
        """

        # Initialize the report we will return.
        num_documents_in_collection_a = collection_a.count_documents({})
        num_documents_in_collection_b = collection_b.count_documents({})
        report = Result(num_documents_in_collection_a, num_documents_in_collection_b)

        # Set up the progress bar functionality.
        self.console.print()
        with Progress(
            console=None if not isinstance(self.console, Console) else self.console,
            disable=not isinstance(self.console, Console),
        ) as progress:
            # Compare the collections, using collection A as the reference.
            #
            # Note: In this stage, we get each document from collection A and check whether it exists in collection B.
            #       If it does, we compare the two documents and display any differences. If it doesn't, we display the
            #       identifier value from collection A (i.e. the identifier value we failed to find in collection B).
            #
            task_a = progress.add_task("Comparing collections, using collection A as reference",
                                    total=num_documents_in_collection_a)
            for document_a in collection_a.find({}):

                # Get the `_id` value from the document from collection A.
                oid_value_a = document_a["_id"]

                # Get the identifier value from the document from collection A.
                if identifier_field_name_a in document_a:
                    identifier_value_a = document_a[identifier_field_name_a]
                else:
                    raise ValueError(
                        f"Document from collection A lacks identifier field: '{identifier_field_name_a}'. "
                        f"Document: {document_a}"
                    )

                # Check whether a document having the same identifier value exists in collection B.
                #
                # Note: If the identifier value from document A was `None`, we use a special filter
                #       (when checking collection B) to disambiguate between documents in which the
                #       identifier field contains `None` and documents in which the identifier field
                #       does not exist at all. MongoDB does not distinguish between those two cases when
                #       we use a basic filter like `{field_name: None}`.
                #
                filter_b: dict = {identifier_field_name_b: identifier_value_a}
                if identifier_value_a is None:
                    filter_b = make_pymongo_filter_for_field_having_value_null(identifier_field_name_b)
                document_b = collection_b.find_one(filter=filter_b)

                # If such a document exists in collection B, compare it to the one from collection A.
                if document_b is not None:
                    are_the_same = self.compare_documents(
                        document_a=document_a,
                        document_b=document_b,
                        ignore_oid=ignore_oid,
                    )

                    if not are_the_same:
                        identifier_value_b = document_b[identifier_field_name_b]
                        self.console.print("Document differs between collections:")

                        # Generate a diff of the two documents' canonical JSON representations.
                        diff_lines: Iterator[str] = self.generate_diff(
                            document_a=document_a,
                            document_b=document_b,
                            label_a=f"Collection A: {identifier_field_name_a}={identifier_value_a!r}",
                            label_b=f"Collection B: {identifier_field_name_b}={identifier_value_b!r}",
                            ignore_oid=ignore_oid,
                        )
                        diff_lines_list = list(diff_lines)  # exhausts the iterator

                        # Update the report.
                        report.identifiers_of_differing_documents.append(identifier_value_a)
                        report.diff_lines_of_differing_documents[oid_value_a] = diff_lines_list

                        # Display a colorized version of the diff.
                        colorized_lines = report.colorize_diff_lines(diff_lines=diff_lines_list)
                        for line in colorized_lines:
                            self.console.print(line)
                        self.console.print()

                else:
                    report.identifiers_of_documents_in_collection_a_only.append(identifier_value_a)
                    self.console.print(
                        f"Document exists in collection A only: "
                        f"[red]{escape(identifier_field_name_a)}={escape(repr(identifier_value_a))}[/red]",
                        highlight=False,
                    )

                # Advance the progress bar by 1.
                progress.update(task_a, advance=1)

            # Compare the collections, using collection B as the reference.
            #
            # Note: In this stage, we get each document from collection B and check whether it exists in collection A.
            #       If it does, we do nothing; since we will have already checked whether the two documents match during
            #       the previous stage (note that this is done under the assumption that the contents of the collections
            #       do not change while this script is running). If it doesn't exist in collection A, we display the
            #       identifier value from collection B (i.e. the identifier value we failed to find in collection A).
            #
            task_b = progress.add_task("Comparing collections, using collection B as reference",
                                    total=num_documents_in_collection_b)
            for document_b in collection_b.find():

                # Get the identifier value from the document from collection B.
                if identifier_field_name_b in document_b:
                    identifier_value_b = document_b[identifier_field_name_b]
                else:
                    raise ValueError(
                        f"Document from collection B lacks identifier field: {identifier_field_name_b}. "
                        f"Document: {document_b}"
                    )

                # Check whether a document having the same identifier value exists in collection A.
                #
                # Note: If the identifier value from document B was `None`, we use a special filter
                #       (when checking collection A) to disambiguate between documents in which the
                #       identifier field contains `None` and documents in which the identifier field
                #       does not exist at all. MongoDB does not distinguish between those two cases when
                #       we use a basic filter like `{field_name: None}`.
                #
                filter_a: dict = {identifier_field_name_a: identifier_value_b}
                if identifier_value_b is None:
                    filter_a = make_pymongo_filter_for_field_having_value_null(identifier_field_name_a)
                document_a = collection_a.find_one(filter=filter_a)

                # If such a document exists in collection B, compare it to the one from collection A.
                if document_a is None:
                    report.identifiers_of_documents_in_collection_b_only.append(identifier_value_b)
                    self.console.print(
                        f"Document exists in collection B only: "
                        f"[green]{escape(identifier_field_name_b)}={escape(repr(identifier_value_b))}[/green]",
                        highlight=False,
                    )

                # Advance the progress bar by 1.
                progress.update(task_b, advance=1)

        return report


def make_pymongo_filter_for_field_having_value_null(field_name: str) -> dict:
    r"""
    Returns a pymongo filter for documents in which the specified field exists and contains `null`.

    This helper function is useful because MongoDB interprets the filter `{"field_name": None}` as
    matching both (a) documents in which the specified field contains `null`, and (b) documents in
    which the specified field does not exist. This helper function disambiguates between the two.

    Reference: https://www.mongodb.com/docs/manual/tutorial/query-for-null-fields/

    >>> make_pymongo_filter_for_field_having_value_null("id")
    {'$and': [{'id': {'$exists': True}}, {'id': None}]}
    """
    return {
        "$and": [
            {field_name: {"$exists": True}},
            {field_name: None},
        ]
    }


@app.command("diff-collections")
def diff_collections(
        mongo_uri_a: Annotated[str, typer.Option(
            envvar="MONGO_URI_A",
            help="Connection string for accessing the MongoDB server containing collection A.",
            show_default=False,
            rich_help_panel="Collection A",
        )],
        database_name_a: Annotated[str, typer.Option(
            help="Name of the database containing collection A.",
            show_default=False,
            rich_help_panel="Collection A",
        )],
        collection_name_a: Annotated[str, typer.Option(
            help="Name of collection A.",
            show_default=False,
            rich_help_panel="Collection A",
        )],
        identifier_field_name_a: Annotated[str, typer.Option(
            help="Name of the field of each document in collection A "
                 "to use to identify a corresponding document in collection B. "
                 "The values in this field must be unique within each collection.",
            rich_help_panel="Collection A",
        )] = "id",
        mongo_uri_b: Annotated[Optional[str], typer.Option(
            envvar="MONGO_URI_B",
            help="Connection string for accessing the MongoDB server containing collection B "
                 "(if different from that specified for collection A).",
            show_default=False,
            rich_help_panel="Collection B",
        )] = None,
        database_name_b: Annotated[Optional[str], typer.Option(
            help="Name of the database containing collection B "
                 "(if different from that specified for collection A).",
            show_default=False,
            rich_help_panel="Collection B",
        )] = None,
        collection_name_b: Annotated[Optional[str], typer.Option(
            help="Name of collection B "
                 "(if different from that specified for collection A).",
            show_default=False,
            rich_help_panel="Collection B",
        )] = None,
        identifier_field_name_b: Annotated[Optional[str], typer.Option(
            help="Name of the field of each document in collection B "
                 "to use to identify a corresponding document in collection A "
                 "(if different from that specified for collection A). "
                 "The values in this field must be unique within each collection.",
            show_default=False,
            rich_help_panel="Collection B",
        )] = None,
        include_oid: Annotated[bool, typer.Option(
            "--include-oid",
            "--include-id",  # support this legacy flag (a misnomer) for backwards compatibility
            help="Include the `_id` field when comparing documents (`--include-id` is deprecated).",
        )] = False,
) -> None:
    r"""
    Compare two MongoDB collections.

    Those collections can reside in either a single database or two separate databases (even across servers).
    """

    # Instantiate a Rich console for fancy console output.
    # Reference: https://rich.readthedocs.io/en/stable/console.html
    console = Console()

    # For any collection B-related options that were omitted, use the values that were specified for collection A.
    database_name_b = database_name_a if database_name_b is None else database_name_b
    collection_name_b = collection_name_a if collection_name_b is None else collection_name_b
    identifier_field_name_b = identifier_field_name_a if identifier_field_name_b is None else identifier_field_name_b
    if mongo_uri_b is None:
        mongo_uri_b = mongo_uri_a

    # Validate the MongoDB connection strings, database names, and collection names.
    collections = []
    for (mongo_uri, is_direct_connection, database_name, collection_name) in [
        (mongo_uri_a, True, database_name_a, collection_name_a),
        (mongo_uri_b, True, database_name_b, collection_name_b),
    ]:
        mongo_client: MongoClient = MongoClient(host=mongo_uri, directConnection=is_direct_connection)
        with (timeout(5)):  # if any message exchange takes > 5 seconds, this will raise an exception

            (host, port_number) = mongo_client.address
            console.print(f'Connecting to MongoDB server: "{host}:{port_number}"')

            # Check whether we can access the MongoDB server.
            mongo_client.server_info()  # raises an exception if it fails

            # Check whether the database exists on the MongoDB server.
            if database_name not in mongo_client.list_database_names():
                raise ValueError(f'Database "{database_name}" not found on the MongoDB server.')

            # Check whether the collection exists in the database.
            database = mongo_client[database_name]
            if collection_name not in database.list_collection_names():
                raise ValueError(f'Collection "{collection_name}" not found in database "{database_name}".')

            # Store a reference to the collection.
            collection = database[collection_name]
            collections.append(collection)

    # Make more intuitive aliases for the collections.
    collection_a = collections[0]
    collection_b = collections[1]

    # Compare the collections with one another.
    comparator = Comparator(console=console)
    report = comparator.compare_collections(
        collection_a=collection_a,
        collection_b=collection_b,
        identifier_field_name_a=identifier_field_name_a,
        identifier_field_name_b=identifier_field_name_b,
        ignore_oid=not include_oid,
    )

    # Display a table summarizing the result.
    console.print()
    console.print(report.get_summary_table())
    console.print()

if __name__ == "__main__":
    app()
