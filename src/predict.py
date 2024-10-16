import argparse
import configparser
from datetime import datetime
import os
import json
import pandas as pd
import pickle
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder
import shutil
import sys
import time
import traceback
import yaml

from db import PostgresDB
from kafka_service import KafkaService
from logger import Logger


SHOW_LOG = True
logger = Logger(SHOW_LOG)
log = logger.get_logger(__name__)

db = PostgresDB()
db.create_table()


def kafka_to_db_listener(data):
    server_response = data.value

    round = server_response["round"]
    air_date_group = server_response["air_date_group"]
    question = server_response["question"]
    value = server_response["value"]

    log.info(f'Kafka DB LISTENER: round: {round}, air_date_group: {air_date_group}, question: {question}, value: {value}')

    db.insert_data(round, air_date_group, question, value)


kafka = KafkaService()
kafka.register_kafka_listener(kafka_to_db_listener)


class Predictor():

    def __init__(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")
        self.parser = argparse.ArgumentParser(description="Predictor")
        self.parser.add_argument("-m",
                                 "--model",
                                 type=str,
                                 help="Select model",
                                 required=True,
                                 default="RAND_FOREST",
                                 const="RAND_FOREST",
                                 nargs="?",
                                 choices=["RAND_FOREST"])
        self.parser.add_argument("-t",
                                 "--tests",
                                 type=str,
                                 help="Select tests",
                                 required=True,
                                 default="smoke",
                                 const="smoke",
                                 nargs="?",
                                 choices=["smoke", "func"])
        self.X_train = pd.read_csv(
            self.config["SPLIT_DATA"]["X_train"], index_col=0)
        self.y_train = pd.read_csv(
            self.config["SPLIT_DATA"]["y_train"], index_col=0)
        self.X_test = pd.read_csv(
            self.config["SPLIT_DATA"]["X_test"], index_col=0)
        self.y_test = pd.read_csv(
            self.config["SPLIT_DATA"]["y_test"], index_col=0)
        self.column_trans = ColumnTransformer([('Round', OneHotEncoder(dtype='int'),['Round']),
                                  ('air_date_group', OneHotEncoder(dtype='int'),['air_date_group']),
                                  ('Question', TfidfVectorizer(stop_words='english'), 'Question')],
                                remainder='drop')
        self.X_train = self.column_trans.fit_transform(self.X_train)
        self.X_test = self.column_trans.transform(self.X_test)
        log.info("Predictor is ready")

    def predict(self) -> bool:
        args = self.parser.parse_args()
        try:
            classifier = pickle.load(
                open(self.config[args.model]["path"], "rb"))
        except FileNotFoundError:
            log.error(traceback.format_exc())
            sys.exit(1)
        if args.tests == "smoke":
            try:
                score = classifier.score(self.X_test, self.y_test)
                print(f'{args.model} has {score} score')
            except Exception:
                log.error(traceback.format_exc())
                sys.exit(1)
            log.info(
                f'{self.config[args.model]["path"]} passed smoke tests')
        elif args.tests == "func":
            tests_path = os.path.join(os.getcwd(), "tests")
            exp_path = os.path.join(os.getcwd(), "experiments")
            for test in os.listdir(tests_path):
                with open(os.path.join(tests_path, test)) as f:
                    try:
                        data = json.load(f)
                        round = str(data["X"][0]["Round"])
                        air_date_group = str(data["X"][0]["air_date_group"])
                        question = str(data["X"][0]["Question"])
                        X = self.column_trans.transform(
                            pd.json_normalize(data, record_path=['X']))
                        y = pd.json_normalize(data, record_path=['y'])
                        score = classifier.score(X, y)
                        prediction = classifier.predict(X)
                        db_data = {
                            "round": round,
                            "air_date_group": air_date_group,
                            "question": question,
                            "value": int(prediction[0])
                        }
                        kafka.send(db_data)
                        # self.db.insert_data(round, air_date_group, question, int(prediction))
                    except Exception:
                        log.error(traceback.format_exc())
                        sys.exit(1)
                    log.info(
                        f'{self.config[args.model]["path"]} passed func test {f.name}')
                    exp_data = {
                        "model": args.model,
                        "model params": dict(self.config.items(args.model)),
                        "tests": args.tests,
                        "score": str(score),
                        "X_test path": self.config["SPLIT_DATA"]["x_test"],
                        "y_test path": self.config["SPLIT_DATA"]["y_test"],
                    }
                    date_time = datetime.fromtimestamp(time.time())
                    str_date_time = date_time.strftime("%Y_%m_%d_%H_%M_%S")
                    exp_dir = os.path.join(exp_path, f'exp_{test[:6]}_{str_date_time}')
                    os.mkdir(exp_dir)
                    with open(os.path.join(exp_dir,"exp_config.yaml"), 'w') as exp_f:
                        yaml.safe_dump(exp_data, exp_f, sort_keys=False)
                    shutil.copy(os.path.join(os.getcwd(), "logfile.log"), os.path.join(exp_dir,"exp_logfile.log"))
                    shutil.copy(self.config[args.model]["path"], os.path.join(exp_dir,f'exp_{args.model}.sav'))
            db.close()
        return True


if __name__ == "__main__":
    predictor = Predictor()
    predictor.predict()