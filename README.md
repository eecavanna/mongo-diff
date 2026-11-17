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

### Installation

Assuming you have `pipx` installed, you can install the tool by running the following command:

```shell
pipx install mongo-diff
```

> [`pipx`](https://pipx.pypa.io/stable/) is a tool people can use to
> [download and install](https://pipx.pypa.io/stable/#where-does-pipx-install-apps-from)
> Python scripts that are hosted on PyPI.
> You can [install `pipx`](https://pipx.pypa.io/stable/installation/) by running `$ python -m pip install pipx`.

### Running

You can display the tool's `--help` snippet by running:

```shell
mongo-diff --help
```

At the time of this writing, the tool's `--help` snippet is:

```console
 Usage: mongo-diff [OPTIONS]

 Compare two MongoDB collections.
 Those collections can reside in either a single database or two separate
 databases (even across servers).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --include-oid,--include-id          Include the `_id` field when comparing   │
│                                     documents (`--include-id` is             │
│                                     deprecated).                             │
│ --help                              Show this message and exit.              │
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
│                                           collection B. The values in this   │
│                                           field must be unique within each   │
│                                           collection.                        │
│                                           [default: id]                      │
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
│                                        for collection A). The values in this │
│                                        field must be unique within each      │
│                                        collection.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

> Note: The above snippet was captured from a terminal window whose width was 80 characters.

#### MongoDB connection strings

As documented in the `--help` snippet above, you can provide the MongoDB connection strings to the tool via either (a)
command-line options; or (b) environment variables named `MONGO_URI_A` and `MONGO_URI_B`. The latter can come in handy
for MongoDB connection strings that contain passwords.

Here's how you could create those environment variables:

```shell  
export MONGO_URI_A='mongodb://localhost:27017'
export MONGO_URI_B='mongodb://username:password@host.example.com:22222'
```

> Note: That will only create those environment variables in the current shell process. You can persist them by adding
> those same commands to your shell initialization script (e.g. `~/.bashrc`, `~/.zshrc`).

#### Example output

As the tool compares the collections, it will display the **differences** it detects; like this:

```diff
Document differs between collections:
--- Collection A: id='x:food-00001'
+++ Collection B: id='x:food-00001'
@@ -13,7 +13,7 @@
       "type": "food"
     }
   ],
-  "name": "Salmon",
+  "name": "Salmon Fillet",
   "vendor": "Alaskan Foods",
   "vendorCountry": "USA",
   "vendorRegion": "Alaska",

Document exists in collection A only: id='x:food-00002'
Document exists in collection A only: id='x:food-00003'
Document exists in collection B only: id='x:food-00004'
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

### Updating

You can update the tool to [the latest version available on PyPI](https://pypi.org/project/mongo-diff/) by running:

```shell
pipx upgrade mongo-diff
```

### Uninstallation

You can uninstall the tool from your computer by running:

```shell
pipx uninstall mongo-diff
```

## Development

We use [uv](https://docs.astral.sh/uv/) to both (a) manage dependencies and (b) build and publish packages to PyPI.

- `pyproject.toml`: Configuration file for `uv` and other tools
- `uv.lock`: Lockfile listing resolved dependencies, direct and indirect (generated via `$ uv lock`)

### Clone repository

```shell
git clone https://github.com/eecavanna/mongo-diff.git
cd mongo-diff
```

### Set up virtual environment and install dependencies

Create the `.venv` virtual environment and install the project's dependencies (including those in the `dev` group):

```shell
uv sync
```

> You can run commands inside the virtual environment using `$ uv run <command>` without activating it,
> or activate it directly via `$ source .venv/bin/activate` (and detach via `$ deactivate`).

### Make changes

Edit the tool's source code and documentation however you want.

While editing the tool's source code, you can run the tool via `uv run` in order to test things out:

```shell
uv run mongo-diff --help
```

### Run tests

We currently only have a smattering of doctests in this codebase. You can run them using [pytest](https://docs.pytest.org/en/stable/) (which is configured in `pyproject.toml` to run doctests automatically) via:

```shell
uv run pytest
```

We may eventually populate the `tests/` directory with a more exhaustive test suite,
using `pytest` and [mongomock](https://pypi.org/project/mongomock/).

### Build package

#### Update package version

PyPI [doesn't allow](https://pypi.org/help/#file-name-reuse) people to publish the same "version" of a package multiple
times.

You can update the version identifier of the package by running:

```shell
uv version {version}
```

Or bump a version component with:

```shell
uv version --bump {keyword}
```

> You can replace `{version}` with a literal version identifier (e.g. `0.3.2`) or `{keyword}` with a bump keyword
> (e.g. `major`, `minor`, or `patch`). You can run `$ uv version --help` to see all options.

Alternatively, you can manually edit the `version` line in `pyproject.toml` (and run `$ uv lock` to update `uv.lock`):

```diff
- version = "0.1.0"
+ version = "0.1.1"
```

#### Build the package

Build the package based upon the latest source code:

```shell
uv build
```

> That will create both a
> [source distribution](https://packaging.python.org/en/latest/specifications/source-distribution-format/)
> file (whose name ends with `.tar.gz`) and a
> [wheel](https://packaging.python.org/en/latest/specifications/binary-distribution-format/#binary-distribution-format)
> file (whose name ends with `.whl`) in the `dist` directory.

### Publish package

#### Set up PyPI credentials

Create the following
[environment variable](https://docs.astral.sh/uv/guides/package/#publishing-your-package),
which `uv` will check for if credentials aren't specified via CLI options:

```shell
export UV_PUBLISH_TOKEN="{api_token}"
```

> Replace `{api_token}` with a [PyPI API token](https://pypi.org/help/#apitoken) whose scope includes
> the PyPI project to which you want to publish the package.

#### Publish package to PyPI

Publish the newly-built package to PyPI:

```shell
uv publish
```

At this point, people will be able to download and install the package from
[PyPI](https://pypi.org/project/mongo-diff/).
