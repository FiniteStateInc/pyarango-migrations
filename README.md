# pyarango-migrations
Python migration utilities for ArangoDB

### CLI Migration Tool

The CLI migration tool is designed to manage and run migration scripts for an Arango database.

#### Running Migrations for a Single Tenant Database

To run migrations, you can use the `run` command via poetry or the `bin/cli.py` script. For example:

```shell
poetry run avocado run \
    --db-host http://localhost:8529 \
    --db-username root \
    --db-password password \
    --db-database test_db
# or alternatively
bin/cli.py migration run --password password --dbname test_db
```

Credentials can also be read from a file using the `--credentials-file` option. For example:

```shell
poetry run avocado run \
    --credentials-file /path/to/creds.json \
    --dbname test_db
````

The credentials should be a JSON file in the following format:

```json
{
  "username": "root",
  "password": "password"
}
```

When running the command without specifying a target, it will use the latest record found in the database as the starting point and execute the upgrade method for each migration located in the migrations' directory. For instance, if the latest migration is labeled as "0005", and the migration directory contains "0006," "0007," and "0008," the tool will execute the upgrade method for each migration in sequential order, including "0008."

#### Specifying a Target Migration

If you want to specify a target version just pass a 4-digit number as an argument. For example:

```shell
poetry run avocado run 0005
```

In this case, if the migration was prior to the latest migration, the downgrade method will be invoked for each migration from the latest down to the target.

If the target migration is after the latest migration, the upgrade method will be invoked for each migration from the latest up to and including the target.

It is important to note that the downgrade process is non-inclusive. If the latest migration is "0005", and you specify a target migration of "0001", the tool will stop at "0002". The migration script for "0001" will not be executed. To remove a migration script "0001", you would need to specify a target version of "0000".

#### Running Migrations for Multiple Tenant Databases

To run migrations for multiple tenant databases, you can use the `run-multi` command. For example:

```shell
bin/cli.py migrate run-multi --credentials-file ./creds.json --tenants-file ./tenants.json 0003
```

As you can see, the command is an extension of the `run` with the only requirements being a path to a file containing the database names and another to the credentials.

The tenant file should be a JSON file with the following format:

```json
[
  {
    "databaseName": "dev_db"
  },
  {
    "databaseName": "test_db"
  },
  {
    "databaseName": "prod_db"
  }
]
```

#### Creating Migration Scripts

To create a new migration script, you can use the create command followed by a brief description. The tool will automatically generate a migration script filename for you. Here's how to create a migration script:

```shell
bin/cli.py run create third_one # should create a file named 0003_third_one.py
```

### Building and Installing the Package

After making updates to your project, follow these steps to build and install the package:

### Step 1: Building the Package

To build the package, run the following command in your project directory:

```shell
poetry build
```

This command will create a distributable package in the `dist` directory of your project.

### Step 2: Installing the Package Locally

#### Using Poetry

You can use Poetry to install the local package directly into your project. Run the following command, replacing `your-package-name-0.1.0-py3-none-any.whl` with the actual package filename:

```shell
poetry add path/to/your-package-name-0.1.0-py3-none-any.whl
```

This adds the package as a dependency to your Poetry project, and Poetry will handle the installation, including any dependencies your package may have.

#### Using pip

Alternatively, you can use `pip` to install the local package into your project:

```shell
pip install dist/your-package-name-0.1.0-py3-none-any.whl
```

### Step 3: Using the CLI Tool

Once the package is installed in your local environment or project, you can use the CLI tool as follows:

```shell
poetry run avocado ...
```

Replace `avocado ...` with the specific command you need to execute using the CLI tool.

By following these steps, you can build, install, and use your package conveniently within your local environment or project.
