# mongo-diff

`mongo-diff` is a command-line tool people can use to compare two MongoDB collections.

Those collections can reside in either a single database or two separate databases (even across servers).

```mermaid
%% This is the source code of a Mermaid diagram, which GitHub will render as a diagram.
%% Note: PyPI does not render Mermaid diagrams, and instead displays their source code.
%%       Reference: https://github.com/pypi/warehouse/issues/13083
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

Part of running `mongo-diff` involves providing MongoDB connection strings to it. If your MongoDB connection strings
contain sensitive information, such as passwords, I'd recommend storing them in **environment variables** instead of
passing them to `mongo-diff` via the command line.

If you don't pass `mongo-diff` your MongoDB connection strings via the command line, `mongo-diff` will
look for them in environment variables named `MONGO_URI_A` and `MONGO_URI_B`.

> You can learn more about those environment variables in the `--help` snippet below.

You can create those environment variables by running the following commands
(replacing the example connection strings with real ones):

```shell  
$ export MONGO_URI_A='mongodb://localhost:27017'
$ export MONGO_URI_B='mongodb://username:password@host.example.com:22222'
```

> Note: That will only create those environment variables in the current shell process. You can persist them by adding
> those same commands to your shell initialization script (e.g. `~/.zshrc`).

### 2. Install the tool.

Assuming you have `pipx` installed, you can install the tool by running the following command:

```shell
pipx install mongo-diff
```

> [`pipx`](https://pipx.pypa.io/stable/) is a tool people can use to
> [download and install](https://pipx.pypa.io/stable/#where-does-pipx-install-apps-from)
> Python scripts that are hosted on PyPI.
>
> You can install `pipx` by running `$ python -m pip install pipx` or via another means
> documented in its [installation guide](https://pipx.pypa.io/stable/installation/).

Installing the tool onto your computer will make the command `mongo-diff` available on your computer.

```console
$ which mongo-diff
/Users/YourName/.local/bin/mongo-diff
```

### 3. Use the tool.

You can display the tool's `--help` snippet by running:

```shell
mongo-diff --help
```

At the time of this writing, the tool's `--help` snippet is:

```console
 Usage: mongo-diff [OPTIONS]

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

> Note: The above snippet was captured from a terminal window whose width was 80 pixels.

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

### 4. (Optional) Update the tool.

You can update the tool to [the latest version available on PyPI](https://pypi.org/project/mongo-diff/) by running:

```shell
pipx upgrade mongo-diff
```

### 5. (Optional) Uninstall the tool.

You can uninstall the tool from your computer by running:

```shell
pipx uninstall mongo-diff
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

From now on, I'll refer to the Poetry virtual environment's shell as the "Poetry shell."

### Install dependencies

At the Poetry shell, install the project's dependencies:

```shell
poetry install
```

### Make changes

Edit the tool's source code and documentation however you want.

### Build package

#### Update package version

PyPI [doesn't allow](https://pypi.org/help/#file-name-reuse) people to publish the same "version" of a package multiple
times.

You can update the version identifier of the package by running:

```shell
poetry version {version_or_keyword}
```

> You can replace `{version_or_keyword}` with either a literal version identifier (e.g. `0.1.1`) or a keyword
> (e.g. `major`, `minor`, or `patch`). You can run `$ poetry version --help` to see the valid keywords.

Alternatively, you can manually edit a line in `pyproject.toml`:

```diff
- version = "0.1.0"
+ version = "0.1.1"
```

#### Build package

At the Poetry shell, build the package based upon the latest source code:

```shell
poetry build
```

> That will create both a
> [source distribution](https://setuptools.pypa.io/en/latest/deprecated/distutils/sourcedist.html#creating-a-source-distribution)
> file (whose name ends with `.tar.gz`) and a
> [wheel](https://packaging.python.org/en/latest/specifications/binary-distribution-format/#binary-distribution-format)
> file (whose name ends with `.whl`) in the `dist` directory.

### Publish package

#### Set up PyPI credentials

At the Poetry shell, create the following
[environment variable](https://python-poetry.org/docs/repositories/#configuring-credentials),
which Poetry will check for if credentials aren't specified to it in another way.

```shell
export POETRY_PYPI_TOKEN_PYPI="{api_token}"
```

> Replace `{api_token}` with a [PyPI API token](https://pypi.org/help/#apitoken) whose scope includes
> the PyPI project to which you want to publish the package.

#### Publish package to PyPI

At the Poetry shell, publish the newly-built package to PyPI:

```shell
poetry publish
```

At this point, people will be able to download and install the package from
[PyPI](https://pypi.org/project/mongo-diff/).
