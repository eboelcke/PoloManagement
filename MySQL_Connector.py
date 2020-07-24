from configparser import ConfigParser
import ySqlConnectionM
import os


class MysqlConnection:

    def __init__(self, filename, filepath=None):
        self.filename = filename
        self.filepath = filepath
        self.configfile = filename if not filepath else os.path.join(filepath, filename)
        self.db = {}
        return

    def read_db_config(self,section='mysql'):
        """ Read database configuration file and return a dictionary object
        :param filename: name of the configuration file
        :param section: section of database configuration
        :return: a dictionary of database parameters
        """
        # create parser and read ini configuration file
        parser = ConfigParser()
        parser.read(self.configfile)

        # get section, default to mysql
        try:
            if parser.has_section(section):
                items = parser.items(section)
                for item in items:
                    self.db[item[0]] = item[1]
                return True, self.db
            else:
                raise Exception('{0} not found in the {1} file'.format(section, self.filename))
        except Exception as err:
            print(err)
            return False, self.db

    def test_connection(self):
        cnx = None
        if len(self.db) != 4:
            print("Connection string incomplete!")
            return False, "Connection string is incomplete"
        try:
            message = "Connecting to server: '{}'........".format(self.db['host'])
            print(message)
            cnx = MySQLConnection(**self.db)
            if cnx.is_connected():
                message = "Communication with the host: '{}' has succeeded".format(self.db['host'])
                print(message)
                return True, message
        except DatabaseError as err:
            message = "Connection to server '{}' failed due to: '{}'".format(self.db['host'], err)
            print(message)
        except InterfaceError as err:
            message = "Is the server running? {}".format(err)
            return False, message
        finally:
            if cnx is not None:
                cnx.close()
            print("Connection has been closed")

    def save_db_config(self, db):
        self.db = db
        if len(self.db) < 4:
            return False, "Incomplete connection string"
        try:
            with open(self.configfile, "w", encoding='utf-8') as fh:
                fh.write("[mysql]\n")
                for key, item in self.db.items():
                    fh.write(key + '=' + item+ "\n")
                return True
        except EnvironmentError as err:
            message = err
        except ValueError as err:
            message = err
        print(message)
        return False

    def load_db_config(self, host, user, database, password):
        self.db = dict(host=host, user=user, database=database, password=password)
        print(self.db)
        return

    def open_connection(self):
        cnx = None
        if len(self.db) != 4:
            print("Connection string incomplete!")
            return False, "Connection string is incomplete"
        try:
            message = "Connecting to server: '{}'........".format(self.db['host'])
            print(message)
            cnx = MySQLConnection(**self.db)
            if cnx.is_connected():
                message = "Connection to server: ´{}' is open".format(self.db['host'])
                print(message)
                return True, cnx
        except DatabaseError as err:
            message = "Connection to server '{}' failed".format(self.db['host'])
            print(message)
            return False, None
        except InterfaceError as err:
            message = "Is the server running? {}".format(err)
            print(message)
            return False, None


def main():
    mycnx = MysqlConnection("config.ini")
    db = mycnx.read_db_config()
    mycnx.test_connection()
    return db


if __name__ == "__main__":
    main()

