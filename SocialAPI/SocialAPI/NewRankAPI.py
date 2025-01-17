from pymongo import MongoClient
from .SocialBasicAPI import SocialBasicAPI
from SocialAPI.Helper import Helper
import sys, time
from datetime import datetime
import urllib
from urllib.parse import quote
import re
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from json.decoder import JSONDecodeError

class NewRankAPI(SocialBasicAPI):

    def __init__(self):
        super(NewRankAPI, self).__init__()
        self.__apiToken = self.cfp.get('api', 'newrank')
        self.__rootPath = Helper().getRootPath()
        self.__mongo_user = urllib.parse.quote_plus(self.cfp.get('mongodb_newrank','user'))
        self.__mongo_pwd = urllib.parse.quote_plus(self.cfp.get('mongodb_newrank','pwd'))
        self.__mongo_host = self.cfp.get('mongodb','host')
        self.__mongo_port = self.cfp.get('mongodb','port')
        self.__newrank_url = self.cfp.get('newrank_platform','url_base')

        self.__mongo_uri = 'mongodb://' + self.__mongo_user + ':' + self.__mongo_pwd + '@' + self.__mongo_host + ':' + self.__mongo_port + '/' + 'newrank'
        self.client = MongoClient(self.__mongo_uri)

    def get_weixin_account_article_content(self,account,from_time,to_time,**kwargs):
        self.logger_access.info("Calling Idata with params {}".format(kwargs))
        client = self.client
        db = client['newrank']
        try:

            url = self.__newrank_url + '/weixin/account/articles_content'
            headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8",'Key':self.__apiToken}

            paramsDict = kwargs.copy()
            paramsDict['account'] = account
            paramsDict['from'] = from_time
            paramsDict['to'] = to_time
            tableName = paramsDict.get('app') + '_' + paramsDict.get('function')
            paramsDict.pop('app')
            paramsDict.pop('function')
            paramsDict.pop('pagelimit')

            page_limit = kwargs.get('pagelimit',5)
            page_num = 1
            loop = True
            total_posts = 0
            retry_num = 0
            retry_max = 5


            while loop and page_num <= page_limit and retry_num < retry_max:
                try:

                    postList = list()

                    paramsDict['page'] = page_num
                    r = self.postRequest(url, paramsDict, headers=headers)
                    res = r.json()

                    if res.get('code') != 0:
                        if res.get('code') == 1203:
                            raise StopIteration
                        else:
                            raise Exception(res.get('msg'))
                    if res.get('code') in (1500,1502,1503,1504): #System Errors
                        retry_num += 1
                        continue
                    postList += res['data']
                    page_num += 1

                    if not postList:
                        self.logger_access.info(
                            'No post returned for {}'.format(tableName))
                        return
                    lookup_keys = ['sn']
                    self.update_mongodb(postList, lookup_keys,**kwargs)
                    total_posts += len(postList)
                    self.logger_access.info(
                        '{} records have been fetched. Totally {} records - {}'.format(len(postList), total_posts,
                                                                                       tableName))
                    time.sleep(0.1)
                except JSONDecodeError as e:
                    raise Exception(e)
                except StopIteration:
                    loop=False
                finally:
                    pass
        except Exception as e:
            class_name = self.__class__.__name__
            function_name = sys._getframe().f_code.co_name
            msg = 'On line {} - {}'.format(sys.exc_info()[2].tb_lineno, e)
            db.newrank_error_log.insert({'className': class_name, 'functionName': function_name, 'params': kwargs,
                                       'createdTime': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), 'msg': msg})
            self.logger_error.error(msg)
            exit(1)

    def get_weixin_data_combine_search_content(self,from_time,to_time,**kwargs):

        self.logger_access.info("Calling Idata with params {}".format(kwargs))
        client = self.client
        db = client['newrank']
        try:

            url = self.__newrank_url + '/weixin/data/combine/search_content'
            headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8",'Key':self.__apiToken}

            paramsDict = kwargs.copy()
            paramsDict['from'] = from_time
            paramsDict['to'] = to_time
            tableName = paramsDict.get('app') + '_' + paramsDict.get('function')
            paramsDict.pop('app')
            paramsDict.pop('function')

            page_limit = kwargs.get('pagelimit',5)
            page_num = 1
            loop = True
            total_posts = 0
            retry_num = 0
            retry_max = 5


            while loop and page_num <= page_limit and retry_num < retry_max:
                try:

                    postList = list()

                    paramsDict['page'] = page_num
                    r = self.postRequest(url, paramsDict, headers=headers)
                    res = r.json()

                    if res.get('code') != 0:
                        if res.get('code') == 1203:
                            raise StopIteration
                        else:
                            raise Exception(res.get('msg'))
                    if res.get('code') in (1500,1502,1503,1504):
                        retry_num += 1
                        continue
                    for _ in res['data']:
                        match_obj = re.search(r'.*&mid=(\w+).*&sn=(\w+)&.*', _['url'])
                        if match_obj:
                            mid = match_obj.group(1)
                            sn = match_obj.group(2)
                            _['mid'] = mid
                            _['sn'] = sn
                        # ugly \udc47 in some keywords list
                        if _.get('keywords'):
                            for i in range(len(_.get('keywords'))):
                                _.get('keywords')[i] = _.get('keywords')[i].encode('utf-8','ignore').decode('utf-8','ignore')
                    postList += res['data']
                    page_num += 1

                    if not postList:
                        self.logger_access.info(
                            'No post returned for {}'.format(tableName))
                        return
                    lookup_keys = ['sn']
                    self.update_mongodb(postList, lookup_keys,**kwargs)
                    total_posts += len(postList)
                    self.logger_access.info(
                        '{} records have been fetched. Totally {} records - {}'.format(len(postList), total_posts,
                                                                                       tableName))
                    time.sleep(0.1)
                except JSONDecodeError as e:
                    raise Exception(e)
                except StopIteration:
                    loop = False
        except Exception as e:
            class_name = self.__class__.__name__
            function_name = sys._getframe().f_code.co_name
            msg = 'On line {} - {}'.format(sys.exc_info()[2].tb_lineno, e)
            db.newrank_error_log.insert({'className': class_name, 'functionName': function_name, 'params': kwargs,
                                       'createdTime': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'), 'msg': msg})
            self.logger_error.error(msg)
            exit(1)


    def update_mongodb(self,postList, lookup_keys,**kwargs):
        try:
            client = self.client
            db = client['newrank']
            paramsDict = kwargs.copy()
            tableName = paramsDict.get('app') + '_' + paramsDict.get('function')
            postTable = db[tableName]

            update_operations = list()
            for post in postList:

                post['updatedTime'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                lookup_dict = {}
                for _ in lookup_keys:
                    lookup_dict[_] = post[_]
                op = UpdateOne(lookup_dict,
                               {'$set': post, '$setOnInsert': {
                                   'createdTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}},
                               upsert=True)

                update_operations.append(op)

            postTable.bulk_write(update_operations, ordered=False, bypass_document_validation=False)

        except BulkWriteError as e:
            raise Exception(e.details)

        except Exception as e:
            self.logger_error.error(e)
            exit(1)

    def __str__(self):
        return "Newrank APIs"