import configparser
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import WhitespaceTokenizer
import numpy as np
import os
import pandas as pd
from sklearn.model_selection import train_test_split
import sys
import traceback

from logger import Logger

TEST_SIZE = 0.3
SHOW_LOG = True

tokenizer = WhitespaceTokenizer()
lemmatizer = WordNetLemmatizer()


class DataMaker():

    def __init__(self) -> None:
        logger = Logger(SHOW_LOG)
        self.config = configparser.ConfigParser()
        self.log = logger.get_logger(__name__)
        self.project_path = os.path.join(os.getcwd(), "data")
        self.data_path = os.path.join(self.project_path, "JEOPARDY_CSV.csv")
        self.X_path = os.path.join(self.project_path, "JEOPARDY_X.csv")
        self.y_path = os.path.join(self.project_path, "JEOPARDY_y.csv")
        self.train_path = [os.path.join(self.project_path, "Train_JEOPARDY_X.csv"), os.path.join(
            self.project_path, "Train_JEOPARDY_y.csv")]
        self.test_path = [os.path.join(self.project_path, "Test_JEOPARDY_X.csv"), os.path.join(
            self.project_path, "Test_JEOPARDY_y.csv")]
        self.log.info("DataMaker is ready")

    def get_data(self) -> bool:
        def binning(value):
            if value < 1000:
                return np.round(value, -2)
            elif value < 10000:
                return np.round(value, -3)
            else:
                return np.round(value, -4)
        def text_preprocessing(text):
            return " ".join([lemmatizer.lemmatize(w) for w in tokenizer.tokenize(text)])
        show_data = pd.read_csv(self.data_path)
        show_data.drop('Show Number', axis=1, inplace=True)
        show_data.rename(columns=lambda x: x.strip(), inplace=True)
        show_data = show_data[~(show_data['Round'].isin(["Final Jeopardy!", "Tiebreaker"]))]
        show_data['Value'] = show_data['Value'].str.replace("$", '')
        show_data['Value'] = show_data['Value'].str.replace(",", '')
        show_data['Value'] = show_data['Value'].astype(int)
        show_data['Air Date'] = pd.to_datetime(show_data['Air Date'])
        show_data['air_date_group'] = show_data['Air Date'].apply(lambda x: 'pre-2002' if x.year < 2002 else 'post-2002')
        show_data.drop('Air Date', axis=1, inplace=True)
        show_data.drop('Answer', axis=1, inplace=True)
        show_data.drop('Category', axis=1, inplace=True)
        show_data['Value'] = show_data['Value'].apply(binning)
        nltk.download("wordnet")
        show_data['Question'] = show_data['Question'].apply(text_preprocessing)
        y = show_data['Value']
        X = show_data[['Round', 'air_date_group', 'Question']]
        X.to_csv(self.X_path, index=True)
        y.to_csv(self.y_path, index=True)
        if os.path.isfile(self.X_path) and os.path.isfile(self.y_path):
            self.log.info("X and y data is ready")
            self.config["DATA"] = {'X_data': self.X_path,
                                   'y_data': self.y_path}
            return os.path.isfile(self.X_path) and os.path.isfile(self.y_path)
        else:
            self.log.error("X and y data is not ready")
            return False

    def split_data(self, test_size=TEST_SIZE) -> bool:
        self.get_data()
        try:
            X = pd.read_csv(self.X_path, index_col=0)
            y = pd.read_csv(self.y_path, index_col=0)
        except FileNotFoundError:
            self.log.error(traceback.format_exc())
            sys.exit(1)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3)
        self.save_splitted_data(X_train, self.train_path[0])
        self.save_splitted_data(y_train, self.train_path[1])
        self.save_splitted_data(X_test, self.test_path[0])
        self.save_splitted_data(y_test, self.test_path[1])
        self.config["SPLIT_DATA"] = {'X_train': self.train_path[0],
                                     'y_train': self.train_path[1],
                                     'X_test': self.test_path[0],
                                     'y_test': self.test_path[1]}
        self.log.info("Train and test data is ready")
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        return os.path.isfile(self.train_path[0]) and\
            os.path.isfile(self.train_path[1]) and\
            os.path.isfile(self.test_path[0]) and \
            os.path.isfile(self.test_path[1])

    def save_splitted_data(self, df: pd.DataFrame, path: str) -> bool:
        df = df.reset_index(drop=True)
        df.to_csv(path, index=True)
        self.log.info(f'{path} is saved')
        return os.path.isfile(path)


if __name__ == "__main__":
    data_maker = DataMaker()
    data_maker.split_data()
