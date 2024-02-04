import dictdiffer
import typer
from typing_extensions import Annotated
from pymongo import MongoClient, timeout
from rich import print as rprint
from rich.progress import Progress

app = typer.Typer(
    add_completion=False,  # hides the shell completion options from `--help` output
)


class Report:
    r"""A report of the differences."""

    def __init__(self, num_documents_in_collection_a: int, num_documents_in_collection_b: int):
        r"""Initializes the report."""
        self.num_documents_in_collection_a = num_documents_in_collection_a
        self.num_documents_in_collection_b = num_documents_in_collection_b
        self.num_documents_in_collection_a_only = 0
        self.num_documents_in_collection_b_only = 0
        self.num_documents_that_differ_across_collections = 0

    def get_summary(self):
        r"""Returns a summary of the report."""
        summary = "\n".join([
            f'Total number of documents in collection A: {self.num_documents_in_collection_a}',
            f'Total number of documents in collection B: {self.num_documents_in_collection_b}',
            f'Number of documents that exist only in collection A: {self.num_documents_in_collection_a_only}',
            f'Number of documents that exist only in collection B: {self.num_documents_in_collection_b_only}',
            f'Number of documents that differ between collections: {self.num_documents_that_differ_across_collections}'
        ])
        return summary


@app.command()
def diff(
        mongo_uri_a: Annotated[str, typer.Option(
            envvar="MONGO_URI_A",
            help="Connection string for accessing the MongoDB server containing collection A",
            show_default=False,
            rich_help_panel="Collection A",
        )],
        database_name_a: Annotated[str, typer.Option(
            help="Name of the database containing collection A",
            show_default=False,
            rich_help_panel="Collection A",
        )],
        collection_name_a: Annotated[str, typer.Option(
            help="Name of collection A",
            show_default=False,
            rich_help_panel="Collection A",
        )],
        identifier_field_name_a: Annotated[str, typer.Option(
            help="Name of the field of each document in collection A "
                 "to use to identify a corresponding document in collection B",
            rich_help_panel="Collection A",
        )] = "id",
        is_direct_connection_a: Annotated[bool, typer.Option(
            "--is-direct-connection-a",
            help="Whether to set the `directConnection` flag when connecting to the MongoDB server containing "
                 "collection A. This can be useful when connecting to a replica set.",
            rich_help_panel="Collection A",
        )] = False,
        mongo_uri_b: Annotated[str, typer.Option(
            envvar="MONGO_URI_B",
            help="Connection string for accessing the MongoDB server containing collection B "
                 "(if different from that specified for collection A)",
            show_default=False,
            rich_help_panel="Collection B",
        )] = None,
        database_name_b: Annotated[str, typer.Option(
            help="Name of the database containing collection B "
                 "(if different from that specified for collection A)",
            show_default=False,
            rich_help_panel="Collection B",
        )] = None,
        collection_name_b: Annotated[str, typer.Option(
            help="Name of collection B "
                 "(if different from that specified for collection A)",
            show_default=False,
            rich_help_panel="Collection B",
        )] = None,
        identifier_field_name_b: Annotated[str, typer.Option(
            help="Name of the field of each document in collection B "
                 "to use to identify a corresponding document in collection A "
                 "(if different from that specified for collection A)",
            show_default=False,
            rich_help_panel="Collection B",
        )] = None,
        is_direct_connection_b: Annotated[bool, typer.Option(
            "--is-direct-connection-b",
            help="Whether to set the `directConnection` flag when connecting to the MongoDB server containing "
                 "collection B. This can be useful when connecting to a replica set. "
                 "Note: If the connection strings for both collections are identical, this option will be ignored.",
            rich_help_panel="Collection B",
        )] = False,
):
    """
    Compare two MongoDB collections, displaying their differences on the console.

    Those collections can reside in either a single database or two separate databases (even across servers).
    """
    # For any collection B-related options that were omitted, use the values that were specified for collection A.
    database_name_b = database_name_a if database_name_b is None else database_name_b
    collection_name_b = collection_name_a if collection_name_b is None else collection_name_b
    identifier_field_name_b = identifier_field_name_a if identifier_field_name_b is None else identifier_field_name_b
    if mongo_uri_b is None:
        mongo_uri_b = mongo_uri_a
        is_direct_connection_b = is_direct_connection_a

    # Validate the MongoDB connection strings, direct connection flags, database names, and collection names.
    collections = []
    for (mongo_uri, is_direct_connection, database_name, collection_name) in [
        (mongo_uri_a, is_direct_connection_a, database_name_a, collection_name_a),
        (mongo_uri_b, is_direct_connection_b, database_name_b, collection_name_b),
    ]:
        mongo_client: MongoClient = MongoClient(host=mongo_uri, directConnection=is_direct_connection)
        with (timeout(5)):  # if any message exchange takes > 5 seconds, this will raise an exception

            (host, port_number) = mongo_client.address
            rprint(f'Connecting to MongoDB server: "{host}:{port_number}"')

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
    report = Report(collection_a.count_documents({}), collection_b.count_documents({}))

    # Set up the progress bar functionality.
    with Progress() as progress:
        # Compare the collections, using collection A as the reference.
        #
        # Note: In this stage, we get each document from collection A and check whether it exists in collection B.
        #       If it does, we compare the two documents and display any differences. If it doesn't, we display the
        #       identifier value from collection A (i.e. the identifier value we failed to find in collection B).
        #
        task_a = progress.add_task("Processing collection A", total=num_documents_in_collection_a)
        for document_a in collection_a.find():
            # Check whether a document having the same identifier value exists in collection B.
            identifier_value_a = document_a[identifier_field_name_a]
            document_b = collection_b.find_one({identifier_field_name_b: identifier_value_a})

            # If such a document exists in collection B, compare it to the one from collection A.
            if document_b is not None:
                differences_generator = dictdiffer.diff(document_a, document_b, ignore=["_id"])
                differences = list(differences_generator)
                if len(differences) > 0:
                    report.num_documents_that_differ_across_collections += 1
                    rprint(f"Documents differ across collections. "
                           f"{identifier_field_name_a}={identifier_value_a},"
                           f"{identifier_field_name_b}={document_b[identifier_field_name_b]}. "
                           f"Differences: {list(differences)}")
            else:
                report.num_documents_in_collection_a_only += 1
                rprint(f"Document exists in collection A only: "
                       f"{identifier_field_name_a}={document_a[identifier_field_name_a]}")

            # Advance the progress bar by 1.
            progress.update(task_a, advance=1)

        # Compare the collections, using collection B as the reference.
        #
        # Note: In this stage, we get each document from collection B and check whether it exists in collection B.
        #       If it does, we do nothing, since we would have already checked whether the two documents match during
        #       the previous stage (note that this is done under the assumption that the contents of the collections
        #       do not change while this script is running). If it doesn't exist in collection A, we display the
        #       identifier value from collection B (i.e. the identifier value we failed to find in collection A).
        #
        task_b = progress.add_task("Processing collection B", total=num_documents_in_collection_b)
        for document_b in collection_b.find():
            # Check whether a document having the same identifier value exists in collection A.
            identifier_value_b = document_b[identifier_field_name_b]
            document_a = collection_a.find_one({identifier_field_name_a: identifier_value_b})

            # If such a document exists in collection B, compare it to the one from collection A.
            if document_a is None:
                report.num_documents_in_collection_b_only += 1
                rprint(f"Document exists in collection B only: "
                       f"{identifier_field_name_b}={document_b[identifier_field_name_b]}")

            # Advance the progress bar by 1.
            progress.update(task_b, advance=1)

        # Display a summary of the result report.
        rprint("\n[bold blue]Result (summary):[/bold blue]")
        rprint(report.get_summary() + "\n")


if __name__ == "__main__":
    app()
