#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @Time    : 2016/6/26 19:17
# @Author  : Eliefly
# @Site    :
# @File    : orm_test.py
# @Software: PyCharm Community Edition

import orm, asyncio, sys, logging

from models import User, Blog, Comment


async def test(loop):
	# 创建数据库连接池，用户名：www-data, 密码：www-data ,访问的数据库为：awesome
	# 在这之前必须现在mysql里创建好awesome数据库，以及对应的表，否则会显示can't connect
	# 可以通过命令行输入：mysql -u root -p < schema.sql ，来执行schema.sql脚本来实现数据库的初始化，schema.sql和本文件在同一目录下
	await orm.create_pool(loop=loop, user='www-data', password='www-data', db='awesome')
	# 创建User对象，即 users table数据
	# u = User(name='test44', email='test44@test.com', passwd='test', image='about:blank')
	# await u.save()

	# --------------------测试count rows语句----------------------
	rows = await User.countRows('id')
	logging.warning('rows is: %s' % rows)

	# -------------------测试insert into语句---------------------
	print('insert users')
	if rows < 2:
		for idx in range(5):
			u = User(name='test%s' % (idx), email='test%s@orm.org' % (idx), passwd='pw', image='about:blank')
			rows = await User.countRows('id', 'email = ?', u.email)
			if rows == 0:
				await u.save()
			else:
				print('the email was already registered...')

	# --------------------测试findAll语句--------------------------
	users = await User.findAll(orderBy='created_at')
	for user in users:
		logging.warning('name: %s, email: %s' % (user.name, user.email))

	# --------------------测试update语句--------------------------
	print('update 1nd user')
	theuser = users[1]
	theuser.email = 'guest@orm.com'
	theuser.name = 'guest'
	await theuser.update()

	users = await User.findAll(orderBy='created_at')
	for user in users:
		logging.warning('name: %s, email: %s' % (user.name, user.email))

	# --------------------测试查找指定用户-------------------------
	print('find the user')
	test_user = await User.find(theuser.id)
	logging.warning('the user name: %s, email: %s' % (theuser.name, theuser.email))

	# --------------------测试delete语句-------------------------
	print('delete 1nd 2nd user')
	users = await User.findAll(orderBy='created_at', limit=(1, 2))
	for user in users:
		logging.warning('delete user: %s' % (user.name))
		await user.remove()  # 不时出现“RuntimeError: Event loop is closed”错误

	users = await User.findAll(orderBy='created_at')
	for user in users:
		logging.warning('name: %s, email: %s' % (user.name, user.email))

# # if __name__ == '__main__':
#     loop = asyncio.get_event_loop()
# 	loop.run_until_complete(test())


if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	loop.run_until_complete( asyncio.wait([test( loop )]) )
	loop.run_until_complete(asyncio.sleep(0))
	loop.close()
	if loop.is_closed():
		sys.exit(0)


# insert users
# WARNING:root:rows is: 0
# WARNING:root:name: test0, email: test0@orm.org
# WARNING:root:name: test1, email: test1@orm.org
# WARNING:root:name: test2, email: test2@orm.org
# WARNING:root:name: test3, email: test3@orm.org
# WARNING:root:name: test4, email: test4@orm.org

# update 1nd user
# WARNING:root:name: test0, email: test0@orm.org
# WARNING:root:name: guest, email: guest@orm.com
# WARNING:root:name: test2, email: test2@orm.org
# WARNING:root:name: test3, email: test3@orm.org
# WARNING:root:name: test4, email: test4@orm.org

# find the user
# WARNING:root:theuser name: guest, email: guest@orm.com

# delete 1nd 2nd user
# WARNING:root:delete user: guest
# WARNING:root:delete user: test2

# WARNING:root:name: test0, email: test0@orm.org
# WARNING:root:name: test3, email: test3@orm.org
# WARNING:root:name: test4, email: test4@orm.org
