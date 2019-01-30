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

            if not postTable.index_information() and paramsDict.get('type') in ('answer','reply','comment'):
                postTable.create_index([('id', 1)])
                postTable.create_index([('publishDate',-1)])
            elif not postTable.index_information() and paramsDict.get('type') not in ('answer','reply','comment'):
                postTable.create_index([('id',1),('ref_date',-1)],unique=True)
                postTable.create_index([('publishDate', -1)])

            postList = []

            loop = True

            while loop:
                try:
                    r = self.getRequest(url, paramsDict)
                    res = r.json()
                    
                    if paramsDict.get('pageToken') and res['retcode'] == '100002':
                        raise Exception('Next Page not Found!')
                    if res['retcode'] != '000000':
                        raise Exception(res['message'])

                    # Remove html column, coz it is too long and useless
                    if tableName in ('weixin_post', 'weixinpro_post'):
                        postDataFrame = pd.DataFrame(res['data'])
                        postDataFrame.drop('html',axis=1,inplace=True)
                        postList += postDataFrame.to_dict('records')
                    else:
                        postList += res['data']
                    self.logger_access.info('{} records have been fetched. Totally {} records - {}'.format(len(postList),res['total'],tableName))
                    time.sleep(0.5)
                    if not res['hasNext']:
                        raise StopIteration
                    paramsDict['pageToken'] = res['pageToken']
                    #self.logger_access.info('pageToken is {}'.format(res['pageToken']))

                except StopIteration:
                    loop = False

            if not postList:
                self.logger_access.info('No post returned between {} and {} for {}'.format(createBeginDate,createEndDate,tableName))
                return

            if paramsDict.get('type') in ('answer','reply','comment'):
                print('{} records before dedup - {}'.format(len(postList),tableName))
                postDataFrame = pd.DataFrame(postList)
                postDataFrame.drop_duplicates('id', inplace=True)
                postList = postDataFrame.to_dict('records')
                print('{} records after dedup - {}'.format(len(postList),tableName))


            for post in postList:
                if not post.get('id'):
                    self.logger_error.error('ID missing with post{} for {}'.format(post,tableName))
                    continue
                post['updatedTime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                x = time.localtime(post['createDate'])
                post['ref_date'] = time.strftime('%Y-%m-%d',x)

                if paramsDict.get('type') in ('answer', 'reply', 'comment'):
                    result = postTable.update_one({'id': post['id']},
                                                  {'$set': post, '$setOnInsert': {
                                                      'createdTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}},
                                                  upsert=True)
                else:
                    result = postTable.update_one({'id': post['id'],'ref_date':post['ref_date']},
                                            {'$set': post, '$setOnInsert': {
                                              'createdTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}},
                                          upsert=True)


        except Exception as e:
            class_name = self.__class__.__name__
            function_name = sys._getframe().f_code.co_name
            msg = 'On line {} - {}'.format(sys.exc_info()[2].tb_lineno, e)
            db.idata_error_log.insert({'className': class_name, 'functionName': function_name, 'params': kwargs,
                                        'createdTime': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), 'msg': msg})
            self.logger_error.error(msg)
