import credentials
import dbinfo
from sqlalchemy import create_engine, text
import datetime


class DBConnector:
    # establish connection with amazon aws rds;
    # engine is meant to only be created once per application process
    # so it should be a class variable that has only one instance
    engine = create_engine("mysql+pymysql://{}:{}@{}:{}/{}".format(
        credentials.DB_USER, credentials.DB_PW, dbinfo.DB_URI, dbinfo.DB_PORT,
        dbinfo.DB_NAME),
        echo=True)

    def create_database(self):
        # text() converts string to compatible sql command
        create_database = text("CREATE DATABASE IF NOT EXISTS dublin_bikes_db")
        # engine.begin() starts a transaction and auto-commits each sql command
        # "with" block would close the connection at the end automatically
        with self.engine.begin() as connection:
            connection.execute(create_database)

    def create_static_station_table(self):
        create_static_station_table = text("""
                CREATE TABLE IF NOT EXISTS station (
                    NUMBER INTEGER NOT NULL,
                    address VARCHAR(128),
                    banking BOOLEAN,
                    NAME VARCHAR(128),
                    position_lat FLOAT,
                    position_long FLOAT,
                    PRIMARY KEY (NUMBER)
                );
            """)
        with self.engine.begin() as connection:
            connection.execute(create_static_station_table)

    def create_dynamic_availability_table(self):
        create_dynamic_availability_table = text("""
                    CREATE TABLE IF NOT EXISTS availability (
                        NUMBER INTEGER NOT NULL,
                        last_update DATETIME NOT NULL,
                        open BOOLEAN,
                        bike_stands INTEGER,
                        available_bikes INTEGER,
                        available_bike_stands INTEGER,
                        PRIMARY KEY (NUMBER, last_update),
                        FOREIGN KEY (NUMBER) REFERENCES station(NUMBER)
                    );
                """)
        with self.engine.begin() as connection:
            connection.execute(create_dynamic_availability_table)

    def test_connection(self):
        check_column_types = text("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_NAME = 'station' OR TABLE_NAME = 'availability'
            """)
        with self.engine.begin() as connection:
            for column in connection.execute(check_column_types):
                print(column)

    def insert_static_data(self, stations):
        with self.engine.begin() as connection:
            for station in stations:
                insert_static = text("""
                    INSERT INTO station(NUMBER, address, banking, NAME, position_lat, position_long)
                    VALUES ({},'{}',{},'{}',{},{});
                                    """
                                     .format(station["number"], self.process_str(station["address"]),
                                             station["banking"],
                                             self.process_str(station["name"]), station["position"]["lat"],
                                             station["position"]["lng"])
                                     )
                connection.execute(insert_static)

    def insert_dynamic_data(self, stations):
        with self.engine.begin() as connection:
            for station in stations:
                # convert timestamp (int type in dictionary) from millisecond to second precision
                timestamp = datetime.datetime.fromtimestamp(station['last_update'] / 1000)
                is_open = True if station['status'] == 'OPEN' else False
                insert_dynamic = text("""
                    INSERT IGNORE INTO availability(NUMBER, last_update, open, 
                        bike_stands, available_bikes, available_bike_stands)
                    VALUES ({},'{}',{},{},{},{});
                                      """
                                      .format(station['number'], timestamp, is_open,
                                              station['bike_stands'], station['available_bikes'],
                                              station['available_bike_stands']
                                              )
                                      )
                connection.execute(insert_dynamic)

    @staticmethod
    def process_str(string):
        # 2 single quotes: first single quote escapes the second in a sql insert query
        return string.replace("'", "''")
