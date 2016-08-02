#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''用来测试orm模块是否可以顺利工作的测试代码'''

__author__ = 'Fanley Huang'

import orm, asyncio, sys, logging

from models import User, Blog, Comment

async def test(loop):
    # 创建数据库连接池，用户名：www-data, 密码：www-data ,访问的数据库为：awesome
    # 在这之前必须现在mysql里创建好awesome数据库，以及对应的表，否则会显示can't connect
    # 可以通过命令行输入：mysql -u root -p < schema.sql ，来执行schema.sql脚本来实现数据库的初始化，schema.sql和本文件在同一目录下
    await orm.create_pool(loop=loop, user='www-data', password='www-data', db='awesome')

    # 测试创建User对象，即 users table数据，ok
    u = User(name='elie', email='elie1@sina.com', passwd='123456', image='about:blank')
    await u.save()

    # 测试创建博客ok
    # b = Blog(user_id='456', user_name='elie', name='1111111', summary='222222',content='3333333', user_image='about:blank')
    # await b.save()


# 不时出现“RuntimeError: Event loop is closed”错误
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete( asyncio.wait([test( loop )]) )  
    loop.run_until_complete(asyncio.sleep(0))
    loop.close()
    if loop.is_closed():
        sys.exit(0)