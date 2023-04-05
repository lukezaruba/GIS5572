# -*- coding: utf-8 -*-
#
# Database Connection for Flask API
# Luke Zaruba
# GIS 5572: ArcGIS II - Lab 3
# 2023-04-06
#

import psycopg2


class Database:
    """
    A class used to represent a database connection.

    Methods
    -------
    initialize_from_env()
        Initializes a database object, based on environmental variable.
    connect()
        Makes connection to database.
    query(query)
        Executes query on database.
    close()
        Closes connection to database.
    """

    def __init__(self, host: str, user: str, password: str, db_name: str, port) -> None:
        """Instantiates a database connection to a PostgreSQL database.

        Args:
            host (str): Host address of the database you would like to access.
            user (str): Username credential for the database you would like to access.
            password (str): Password credential for the database you would like to access.
            db_name (str): Name of the database that you would like to access.
            port (int): Port number of database.
        """
        self.host = host
        self.user = user
        self.password = password
        self.db_name = db_name
        self.port = port

        # Set Connection to None
        self.connection = None

    @classmethod
    def initialize_from_env(cls) -> None:
        """Instantiates a database connection to a PostgreSQL database using enviornmental variables."""
        # Extract Secrets
        host = os.environ.get("HOST")
        user = os.environ.get("USER")
        password = os.environ.get("PASSWORD")
        db_name = os.environ.get("DBNAME")
        port = os.environ.get("DBPORT")

        # Return Instance
        return cls(host, user, password, db_name, port)

    def connect(self) -> None:
        """Makes connection to database."""
        self.connection = psycopg2.connect(
            host=self.host,
            database=self.db_name,
            user=self.user,
            password=self.password,
            port=self.port,
        )

    def query(self, query: str) -> str:
        """Executes a query on a database connection. A connection should already exist.

        Args:
            query (str): A SQL query that will be executed.

        Returns:
            str: The return from the SQL query.
        """
        # Open Cursor
        with self.connection.cursor() as c:
            # Try to Execute
            try:
                # Execute Query
                c.execute(query)

                # Commit to DB
                self.connection.commit()

                # Return Output
                return c.fetchall()

            except Exception as e:
                # Roll Back Transaction if Invalid Query
                self.connection.rollback()

                # Display Error
                return "Error: " + e

    def close(self):
        """Closes connection to database."""
        # Close Connection
        self.connection.close()

        # Set Connection to None
        self.connection = None
