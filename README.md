# mongo-diff

`mongo-diff` is a command-line tool people can use to compare two MongoDB collections.

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

### 1. (Optional) Create environment variables.

Part of running `mongo-diff` involves providing MongoDB connection strings to it. Since MongoDB connection strings
sometimes contain sensitive information, I recommend storing them in **environment variables** instead of specifying
them via CLI options to `mongo-diff`.

> I think that will make it less likely that they are accidentally included in copy/pasted console output or in
> technical demonstrations.

`mongo-diff` is pre-programmed to look for two environment variables: `MONGO_URI_A` and `MONGO_URI_B`.

> You can learn more about those environment variables in the `--help` snippet below.

You can create those environment variables by running the following commands
(replacing the example connection strings with real ones):

```shell  
$ export MONGO_URI_A='mongodb://localhost:27017'
$ export MONGO_URI_B='mongodb://username:password@host.example.com:22222'
```

> Note: That will only create those environment variables in the current shell process. You can persist them by adding
> those same commands to your shell initialization script (e.g. `~/.zshrc`).

### 2. Set up virtual environment.

```shell
# If you don't have Poetry installed yet...
$ pipx install poetry

# Create a Poetry virtual environment and attach to its shell:
$ poetry shell

# At the Poetry virtual environment's shell, install the project's production dependencies:
$ poetry install --only main
```

### 3. Use the tool.

At the Poetry virtual environment's shell, run the `mongo_diff/mongo_diff.py` script as shown in the `--help` snippet below.

```console
$ python mongo_diff/mongo_diff.py --help

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

#### Example output

As the tool compares the collections, it will display the **differences** it detects; like this:

```console
Documents differ between collections: id=1,id=1. Differences: [('change', 'name', ('Joe', 'Joseph'))]
Document exists in collection A only: id=2
Document exists in collection A only: id=4
Document exists in collection B only: id=5
```

When the tool finishes comparing the collections, it will display a **summary** of the result; like this:

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

## Development

We use [Poetry](https://python-poetry.org/) to both (a) manage dependencies and (b) publish packages to PyPI.

- `pyproject.toml`: Configuration file for Poetry and other tools (was generated via `$ poetry init`)
- `poetry.lock`: List of dependencies, direct and indirect (was generated via `$ poetry update`)

### Create virtual environment

Create a Poetry virtual environment and attach to its shell:

```shell
poetry shell
```

> You can see information about the Poetry virtual environment by running: `$ poetry env info`

> You can detach from the Poetry virtual environment's shell by running: `$ exit`

### Install dependencies

At the Poetry virtual environment's shell, install the project's dependencies:

```shell
poetry install
```
