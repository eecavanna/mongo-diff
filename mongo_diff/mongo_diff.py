from difflib import unified_diff
from typing import Iterator, Optional

import dictdiffer
import typer
from typing_extensions import Annotated
from pymongo import MongoClient, timeout
from bson import json_util
from rich.console import Console
from rich.markup import escape
from rich.table import Table, Column
from rich.progress import Progress
from rich import box

app = typer.Typer(
    help="Compare two MongoDB collections.",
    add_completion=False,  # hides the shell completion options from `--help` output
)

# Instantiate a Rich console for fancy console output.
# Reference: https://rich.readthedocs.io/en/stable/console.html
console = Console()


class Result:
    r"""The result of the comparison."""

    def __init__(self, num_documents_in_collection_a: int, num_documents_in_collection_b: int) -> None:
        r"""Initializes the result."""
        self.num_documents_in_collection_a = num_documents_in_collection_a
        self.num_documents_in_collection_b = num_documents_in_collection_b
        self.num_documents_in_collection_a_only = 0
        self.num_documents_in_collection_b_only = 0
        self.num_documents_that_differ_across_collections = 0

    @staticmethod
    def colorize_if(raw_string: str, condition: bool, color: str) -> str:
        r"""Surrounds the raw string with Rich color tags if the condition is true."""
        return f"[{color}]{raw_string}[/{color}]" if condition else raw_string

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
                      self.colorize_if(raw_string=str(self.num_documents_that_differ_across_collections),
                                       condition=self.num_documents_that_differ_across_collections > 0,
                                       color="red"))
        return table


class Comparator():
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
                 "to use to identify a corresponding document in collection B.",
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
                 "(if different from that specified for collection A).",
            show_default=False,
            rich_help_panel="Collection B",
        )] = None,
        include_oid: Annotated[bool, typer.Option(
            "--include-oid",
            "--include-id",  # support this legacy flag (a misnomer) for backwards compatibility
            help="Includes the `_id` field when comparing documents.",
        )] = False,
) -> None:
    r"""
    Compare two MongoDB collections.

    Those collections can reside in either a single database or two separate databases (even across servers).
    """
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

    # Initialize the report we will display later.
    num_documents_in_collection_a = collection_a.count_documents({})
    num_documents_in_collection_b = collection_b.count_documents({})
    report = Result(num_documents_in_collection_a, num_documents_in_collection_b)

    # Set up the progress bar functionality.
    console.print()
    with Progress(console=console) as progress:
        # Compare the collections, using collection A as the reference.
        #
        # Note: In this stage, we get each document from collection A and check whether it exists in collection B.
        #       If it does, we compare the two documents and display any differences. If it doesn't, we display the
        #       identifier value from collection A (i.e. the identifier value we failed to find in collection B).
        #
        task_a = progress.add_task("Comparing collections, using collection A as reference",
                                   total=num_documents_in_collection_a)
        for document_a in collection_a.find({}):

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
                comparator = Comparator()
                are_the_same = comparator.compare_documents(
                    document_a=document_a,
                    document_b=document_b,
                    ignore_oid=not include_oid,
                )

                if not are_the_same:
                    report.num_documents_that_differ_across_collections += 1
                    identifier_value_b = document_b[identifier_field_name_b]
                    console.print("Document differs between collections:")

                    # Display a colorized diff of the two documents' canonical JSON representations.
                    diff_lines = comparator.generate_diff(
                        document_a=document_a,
                        document_b=document_b,
                        label_a=f"Collection A: {identifier_field_name_a}={identifier_value_a!r}",
                        label_b=f"Collection B: {identifier_field_name_b}={identifier_value_b!r}",
                        ignore_oid=not include_oid,
                    )
                    for line in diff_lines:
                        if line.startswith("+"):
                            console.print(line, style="green", highlight=False, markup=False)
                        elif line.startswith("-"):
                            console.print(line, style="red", highlight=False, markup=False)
                        else:
                            console.print(line, highlight=False, markup=False)
                    console.print()

            else:
                report.num_documents_in_collection_a_only += 1
                console.print(
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
                report.num_documents_in_collection_b_only += 1
                console.print(
                    f"Document exists in collection B only: "
                    f"[green]{escape(identifier_field_name_b)}={escape(repr(identifier_value_b))}[/green]",
                    highlight=False,
                )

            # Advance the progress bar by 1.
            progress.update(task_b, advance=1)

    # Display a table summarizing the result.
    console.print()
    console.print(report.get_summary_table())
    console.print()


if __name__ == "__main__":
    app()
