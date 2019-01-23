from pymongo import MongoClient
from .SocialBasicAPI import SocialBasicAPI
from SocialAPI.Helper import Helper
import sys, time
from datetime import datetime
import urllib
from urllib.parse import quote
import pandas as pd

class IdataAPI(SocialBasicAPI):

    def __init__(self):
        super(IdataAPI, self).__init__()
        self.__apiToken = self.cfp.get('api', 'idata')
        self.__rootPath = Helper().getRootPath()
        self.__mongo_user = urllib.parse.quote_plus(self.cfp.get('mongodb_idata','user'))
        self.__mongo_pwd = urllib.parse.quote_plus(self.cfp.get('mongodb_idata','pwd'))
        self.__mongo_host = self.cfp.get('mongodb','host')
        self.__mongo_port = self.cfp.get('mongodb','port')
        self.__idata_url = self.cfp.get('idata_platform','url')

        self.__mongo_uri = 'mongodb://' + self.__mongo_user + ':' + self.__mongo_pwd + '@' + self.__mongo_host + ':' + self.__mongo_port + '/' + 'idata'
        self.client = MongoClient(self.__mongo_uri)
        #self.client = MongoClient()

    def getZanDouData(self, createBeginDate, createEndDate, **kwargs):

        self.logger_access.info("Calling getZanDouData with params {}".format(kwargs))
        try:
            client = self.client
            db = client['idata']

            url = self.__idata_url
            paramsDict = kwargs.copy()
            paramsDict['apikey'] = self.__apiToken
            paramsDict['createBeginDate'] = createBeginDate
            paramsDict['createEndDate'] = createEndDate


            tableName = paramsDict.get('appCode') + '_' + paramsDict.get('type')
            postTable = db[tableName]
            postList = []

            loop = True

            while loop:
                try:
                    r = self.getRequest(url, paramsDict)
                    res = r.json()
                    if res['retcode'] != '000000':
                        raise Exception(res['message'])

                    # Remove html column, coz it is too long and useless
                    if tableName == 'weixin_post':
                        postDataFrame = pd.DataFrame(res['data'])
                        postDataFrame.drop('html',axis=1,inplace=True)
                        postList += postDataFrame.to_dict('records')
                    else:
                        postList += res['data']
                    self.logger_access.info('{} records have been fetched. Totally {} records'.format(len(postList),res['total']))
                    time.sleep(0.5)
                    if not res['hasNext']:
                        raise StopIteration
                    paramsDict['pageToken'] = res['pageToken']
                    self.logger_access.info('pageToken is {}'.format(res['pageToken']))
                except StopIteration:
                    loop = False

            if not postList:
                self.logger_access.info('No post returned in between {} and {}'.format(createBeginDate,createEndDate))
                return

            for post in postList:
                if not post.get('id'):
                    self.logger_error.error('ID missing with post{}'.format(post))
                    continue
                post['updatedTime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                #result = postTable.insert_one(post)
                result = postTable.update_one({'id': post['id']},
                                          {'$set': post, '$setOnInsert': {
                                              'createdTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}},
                                          upsert=True)


        except Exception as e:
            class_name = self.__class__.__name__
            function_name = sys._getframe().f_code.co_name
            msg = 'On line {} - {}'.format(sys.exc_info()[2].tb_lineno, e)
            db.idata_error_log.insert({'className': class_name, 'functionName': function_name, 'params': kwargs,
                                        'createdTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'msg': msg})
            self.logger_error.error(msg)