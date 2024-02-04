# mongo-diff

`mongo-diff` is a command-line script people can use to compare two MongoDB collections.

Those collections can reside in either a single database or two separate databases (even across servers).

```mermaid
graph LR
    script[["mongo_diff.py"]]
    result["List of<br>differences"]

    subgraph s1 \[Server]
        subgraph d1 \[Database]
            collection_a[("Collection A")]
        end
    end

    subgraph s2 \[Server]
        subgraph d2 \[Database]
            collection_b[("Collection B")]
        end
    end

    collection_a --> script
    collection_b --> script
    script --> result
```

## Usage

### Install dependencies

You can install the Python packages upon which this script depends, by running:

```shell
python -m pip install typer rich dictdiffer pymongo
```

- [`typer`](https://typer.tiangolo.com/): CLI framework (`typer` is to `click` as `fastapi` is to `flask`)
- [`rich`](https://rich.readthedocs.io/en/stable/index.html): To format console output
- [`dictdiffer`](https://dictdiffer.readthedocs.io/en/latest/): To compare dictionaries
- [`pymongo`](https://pymongo.readthedocs.io/en/stable/): To access MongoDB servers

### Create environment variables

See the `--help` snippet below for documentation about the `MONGO_URI_A` and `MONGO_URI_B` environment variables.

### Run the script

Run the script as shown in the `--help` snippet below.

```console
$ python mongo_diff.py --help

 Usage: mongo_diff.py [OPTIONS]

 Compare two MongoDB collections, displaying their differences on the console.
 Those collections can reside in either a single database or two separate
 databases (even across servers).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --include-id    --no-include-id      Includes the `_id` field when comparing │
│                                      documents.                              │
│                                      [default: no-include-id]                │
│ --help                               Show this message and exit.             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Collection A ───────────────────────────────────────────────────────────────╮
│ *  --mongo-uri-a                    TEXT  Connection string for accessing    │
│                                           the MongoDB server containing      │
│                                           collection A.                      │
│                                           [env var: MONGO_URI_A]             │
│                                           [required]                         │
│ *  --database-name-a                TEXT  Name of the database containing    │
│                                           collection A.                      │
│                                           [required]                         │
│ *  --collection-name-a              TEXT  Name of collection A. [required]   │
│    --identifier-field-name-a        TEXT  Name of the field of each document │
│                                           in collection A to use to identify │
│                                           a corresponding document in        │
│                                           collection B.                      │
│                                           [default: id]                      │
│    --is-direct-connection-a               Sets the `directConnection` flag   │
│                                           when connecting to the MongoDB     │
│                                           server containing collection A.    │
│                                           This can be useful when connecting │
│                                           to a replica set.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Collection B ───────────────────────────────────────────────────────────────╮
│ --mongo-uri-b                    TEXT  Connection string for accessing the   │
│                                        MongoDB server containing collection  │
│                                        B (if different from that specified   │
│                                        for collection A).                    │
│                                        [env var: MONGO_URI_B]                │
│ --database-name-b                TEXT  Name of the database containing       │
│                                        collection B (if different from that  │
│                                        specified for collection A).          │
│ --collection-name-b              TEXT  Name of collection B (if different    │
│                                        from that specified for collection    │
│                                        A).                                   │
│ --identifier-field-name-b        TEXT  Name of the field of each document in │
│                                        collection B to use to identify a     │
│                                        corresponding document in collection  │
│                                        A (if different from that specified   │
│                                        for collection A).                    │
│ --is-direct-connection-b               Sets the `directConnection` flag when │
│                                        connecting to the MongoDB server      │
│                                        containing collection B. Note: If the │
│                                        connection strings for both           │
│                                        collections are identical, this       │
│                                        option will be ignored.               │
╰──────────────────────────────────────────────────────────────────────────────╯
```

> Note: The above `--help` snippet was captured from a terminal window whose width was 80 pixels.

#### Example invocation

Here's an example invocation of the script:

```console
# (Optional) Create environment variables containing MongoDB connection strings.  
$ export MONGO_URI_A='mongodb://localhost:27017'
$ export MONGO_URI_B='mongodb://username:password@host.example.com:22222'

# Run the script.
$ python mongo_diff.py --database-name-a company --collection-name-a employees
```

While the script compares the collections, it will display the **differences** it detects; like this:

```console
Documents differ between collections: id=1,id=1. Differences: [('change', 'name', ('Joe', 'Joseph'))]
Document exists in collection A only: id=2
Document exists in collection A only: id=4
Document exists in collection B only: id=5
```

When the script finishes comparing the collections, it will display a **summary** of the situation; like this:

```console
                         Result                         
╭───────────────────────────────────────────┬──────────╮
│ Description                               │ Quantity │
├───────────────────────────────────────────┼──────────┤
│ Documents in collection A                 │        4 │
│ Documents in collection B                 │        3 │
├───────────────────────────────────────────┼──────────┤
│ Documents in collection A only            │        2 │
│ Documents in collection B only            │        1 │
├───────────────────────────────────────────┼──────────┤
│ Documents that differ between collections │        1 │
╰───────────────────────────────────────────┴──────────╯
```