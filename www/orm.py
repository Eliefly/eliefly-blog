#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Fanley Huang'

import asyncio
import logging
import aiomysql


def log(sql, args=()):
	logging.info('SQL: %s' % sql)


# The library provides connection pool as well as plain Connection objects.
# pool = yield from aiomysql.create_pool(host='127.0.0.1', port=3306,
#                                            user='root', password='',
#                                            db='mysql', loop=loop)
@asyncio.coroutine
def create_pool(loop, **kw):
	'''
	创建连接池.
	'''
	logging.info('create database connection pool...')
	# py的变量可以指向函数，当然也可以指向generator和corotine
	global __pool
	# 创建数据库连接池
	# A coroutine that creates a pool of connections to MySQL database.
	__pool = yield from aiomysql.create_pool(loop=loop,  # 传递消息循环对象loop用于异步执行，loop – is an optional event loop instance
			# 获取dict['key']的value，必须指定没有默认值
			user=kw['user'],  # 数据库用户名，必须指定
			password=kw['password'],  # 用户密码，必须指定
			db=kw['db'],  # 数据库名，必须指定
			# dict 提供的 get 方法，如果 key 不存在，返回默认的 value
			host=kw.get('host', 'localhost'),  # 默认定义host名字为localhost
			port=kw.get('port', 3306),  # 默认定义mysql的默认端口是3306
			charset=kw.get('charset', 'utf8'),  # 默认数据库字符集是utf8
			autocommit=kw.get('autocommit', True),  # 默认自动提交事务
			maxsize=kw.get('maxsize', 10),  # 默认连接池最最多10个请求
			minsize=kw.get('minsize', 1),  # 默认连接池最少1个请求
	)


# Cursors are created by the Connection.cursor() coroutine: they are bound
# to the connection for the entire lifetime and all the commands are executed
# in the context of the database session wrapped by the connection.

# select函数，负责查询
@asyncio.coroutine
def select(sql, args, size=None):
	'''
	要执行SELECT语句，我们用select函数执行
	'''
	log(sql, args)
	global __pool
	logging.info('select = %s and args = %s' % (sql, args))
	# 从连接池取一个conn出来，with..as..会在运行完后把conn放回连接池
	# getting connection from pool of connections
	with (yield from __pool) as conn:
		# A cursor which returns results as a dictionary. All methods and arguments same as Cursor.
		cur = yield from conn.cursor(aiomysql.DictCursor)  # create dict cursor
		# cursor.execute("SELECT Host, User FROM user"):execute sql query
		yield from cur.execute(sql.replace('?', '%s'), args or ())  # ?号以%s代替，然后%s格式输入args，最后执行execute
		if size:
			rs = yield from cur.fetchmany(size)  # 每次调用取出size个结果
		else:
			rs = yield from cur.fetchall()  # 取出所有结果
		yield from cur.close()  # 关闭cursor
		logging.info('rows returned: %s' % len(rs))
		return rs


# create default cursor
#     cursor = yield from conn.cursor()
@asyncio.coroutine
def execute(sql, args, autocommit=True):  # execute(query, args=None)
	'''
	要执行INSERT、UPDATE、DELETE语句，可以定义一个通用的execute()函数，
	因为这3种SQL的执行都需要相同的参数，以及返回一个整数表示影响的行数
	'''
	log(sql)
	# 从连接池取一个conn出来，with..as..会在运行完后把conn放回连接池
	with (yield from __pool) as conn:
		if not autocommit:
			yield from conn.begin()
		try:
			cur = yield from conn.cursor()
			yield from cur.execute(sql.replace('?', '%s'), args)
			affected = cur.rowcount  # 使用cur.rowcount获取结果集的条数
			yield from cur.close()  # 关闭cursor
			if not autocommit:
				yield from conn.commit()
		except BaseException as e:
			if not autocommit:
				# 事务回滚，为了保证数据的有效性。有时候会存在一个事务包含多个操作，而多个操作又都有
				# 顺序，顺序执行操作时，有一个执行失败，则之前操作成功的也会回滚，即未操作的状态。
				yield from conn.rollback()
			raise
		return affected


# 构造sql语句参数字符串，最后返回的字符串会以','分割多个'?'，如 num==3，则会返回 '?, ?, ?'
# >>> create_args_string(3)
# '?, ?, ?'
def create_args_string(num):
	'''
	创建sql语句中的占位符'?'
	'''
	L = []
	for n in range(num):
		L.append('?')
	return ', '.join(L)


# 定义 Field 类，它负责保存数据库表的字段名和字段类型
class Field(object):
	def __init__(self, name, column_type, primary_key, default):
		self.name = name # 字段名
		self.column_type = column_type # 字段类型
		self.primary_key = primary_key # 是否为主键
		self.default = default # 默认值

	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


# 在 Field 的基础上，进一步定义各种类型的 Field
class StringField(Field):
	# default=None表示没有默认值，
	def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
		super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):
	def __init__(self, name=None, default=False):
		super().__init__(name, 'boolean', False, default)


class IntegerField(Field):
	def __init__(self, name=None, primary_key=False, default=0):
		super().__init__(name, 'bigint', primary_key, default)


class FloatField(Field):
	def __init__(self, name=None, primary_key=False, default=0.0):
		super().__init__(name, 'real', primary_key, default)


class TextField(Field):
	def __init__(self, name=None, default=None):
		super().__init__(name, 'text', False, default)

	# 定义 ModelMetaclass 元类
	# 该元类主要使得Model基类具备以下功能:
	# 1.任何继承自Model的类（比如User），会自动通过ModelMetaclass扫描映射关系
	# 并存储到自身的类属性如__table__、__mappings__中
	# 2.创建了一些默认的SQL语句


class ModelMetaclass(type):
	# __new__拦截类的创建，此处是拦截 Model 类的创建，修改它的属性。
	# __new__ 是在__init__之前被调用的特殊方法
	# __new__是用来创建对象并返回之的方法
	# __new__()方法接收到的参数依次是：
	# 1、当前准备创建的类的对象，就像在普通的类方法中的self参数，即 ModelMetaclass 元类，它是type类的对象，仍是类。
	# 2、类的名字，调用此元类最终创建出实例的类的名字，此处分别是User，Blog，Comment。
	# 3、类继承的父类集合，调用此元类最终创建出实例的类的父类，User，Blog，Comment的父类都是Model。
	# 4、类的方法集合，分别是User，Blog，Comment类的方法集合。
	def __new__(cls, name, bases, attrs):
		if name == 'Model':
			return type.__new__(cls, name, bases, attrs)
			# print('1.', cls)
			# print('2.', name)
			# print('3.', bases)
			# print('4.', attrs)
			# 1. <class 'orm.ModelMetaclass'>
			# 2. User
			# 3. (<class 'orm.Model'>,)
			# 4. {'__table__': 'users', 'image': <orm.StringField object at 0x02987AB0>, 'email': <orm.StringField object at 0x02969E90>, '__qualname__': 'User', '__module__': 'models', 'name': <orm.StringField object at 0x02987A90>, 'admin': <orm.BooleanField object at 0x02969EF0>, 'id': <orm.StringField object
			# at 0x02969E50>, 'passwd': <orm.StringField object at 0x02969E70>, 'created_at': <orm.FloatField object at 0x02987AD0>}
			# 1. <class 'orm.ModelMetaclass'>
			# 2. Blog
			# 3. (<class 'orm.Model'>,)
			# 4. {'__table__': 'blogs', 'created_at': <orm.FloatField object at 0x02987C70>, 'user_id': <orm.StringField object at 0x02987BB0>, '__qualname__': 'Blog', '__module__': 'models', 'user_name': <orm.StringField object at 0x02987BD0>, 'summary': <orm.StringField object at 0x02987B70>, 'name': <orm.Strin
			# gField object at 0x02987C50>, 'id': <orm.StringField object at 0x02987AF0>, 'user_image': <orm.StringField object at 0x02987C30>, 'content': <orm.TextField object at 0x02987B90>}
			# 1. <class 'orm.ModelMetaclass'>
			# 2. Comment
			# 3. (<class 'orm.Model'>,)
			# 4. {'__table__': 'comments', 'blog_id': <orm.StringField object at 0x02987CF0>, 'user_id': <orm.StringField object at 0x02987CB0>, '__qualname__': 'Comment', '__module__': 'models', 'user_name': <orm.StringField object at 0x02987CD0>, 'user_iamge': <orm.StringField object at 0x02987D10>, 'id': <orm.

		tableName = attrs.get('__table__', None) or name  # 获取表名
		logging.info('found model: %s (table: %s)' % (name, tableName))
		# orm.py[line:146] INFO found model: User (table: users)
		# 在当前类（比如User）中查找定义的类的所有属性，如果找到一个Field属性，就把它保存到一个 mappings 的dict对象中。
		mappings = dict()
		fields = []  # fields数组，存放除了主键以外的属性名
		primaryKey = None
		for k, v in attrs.items():
			if isinstance(v, Field):  # 查看value是否属于 Field 类型
				logging.info('  found mapping: %s ==> %s' % (k, v))
				mappings[k] = v  # mappings字典，存放所有 Field 键值对
				if v.primary_key:
					# 找到主键:
					if primaryKey:
						raise RuntimeError('Duplicate primary key for field: %s' % k)  # 如果再找到主键，则报错，主键的唯一性。
					primaryKey = k  # 记录主键
				else:
					fields.append(k)  # 记录不是主键的属性的 key 值
		if not primaryKey:
			raise RuntimeError('Primary key not found.')  # 如果没有主见则报错
		for k in mappings.keys():  # 遍历属性的value值是 Field 的key值
			attrs.pop(k)  # 把类的方法集合中的属于Field类型的从attrs中移除
		# print(k)
		# 以下User类的属性的value值都是Field的类型。
		# email
		# password
		# id
		# name

		escaped_fields = list(map(lambda f: '`%s`' % f, fields))  # 把 fields 的值全部加了个 ``
		attrs['__mappings__'] = mappings  # 保存属性和列的关系,赋值给特殊类变量__mappings__
		# print(attrs['__mappings__'])    # dict实例，key为字符串，values为Field对象。
		# {'name': <__main__.StringField object at 0x02987F30>,
		# 'password': <__main__.StringField object at 0x02987F70>,
		# 'id': <__main__.StringField object at 0x02987F10>,
		# 'email': <__main__.StringField object at 0x02987F50>}
		# print('\n')
		attrs['__table__'] = tableName
		attrs['__primary_key__'] = primaryKey  # 主键属性名'id'
		attrs['__fields__'] = fields  # 除主键外的属性名:['password', 'name', 'email']
		# 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
		# select `id`, `email`, `password`, `name` from `User`
		attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
		# insert into `User` (`name`, `password`, `email`, `id`) values (?, ?, ?, ?)
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (
			tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
		# update `User` set `username`=?, `password`=?, `email`=? where `id`=?
		# map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)表示如果创建Field实例没传入name参数 则使用Model中的属性名
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (
			tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		# delete from `User` where `id`=?
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
		# 返回元类
		return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):
	'''
	Model类具有增删改查功能
	Model从dict继承，所以具备所有dict的功能，同时又实现了特殊方法__getattr__()和__setattr__()，因此又可以像引用普通字段那样写：
	>>> user['id']
	123
	>>> user.id
	123
	'''

	def __init__(self, **kw):
		super(Model, self).__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)

	def __setattr__(self, key, value):
		self[key] = value

	def getValue(self, key):
		return getattr(self, key, None)

	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				# 判读value是属性还是可调用的方法
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' % (key, str(value)))
				setattr(self, key, value)
		return value

	# -------------往Model类添加class方法，就可以让所有子类调用class方法：---------------#
	# classmethod是用来指定一个类的方法为类方法，没有此参数指定的类的方法为实例方法，类方法既可以直接类调用(C.f())，也可以进行实例调用(C().f())。：
	# 所有这些方法都用@asyncio.coroutine装饰，变成一个协程:

	# Example: Comment.findAll('blog_id=?', [id], orderBy='created_at desc',limit=(page.offset, page.limit))
	@classmethod
	@asyncio.coroutine
	def findAll(cls, where=None, args=None, **kw):
		' find objects by where clause. '
		sql = [cls.__select__]
		if where:  # 如果有where
			sql.append('where')  # 加关键字
			sql.append(where)  # 加参数
		if args is None:  # args参数为空
			args = []
		orderBy = kw.get('orderBy', None)  # kw参数有无orderBy
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		limit = kw.get('limit', None)  # kw参数有无limit
		if limit is not None:
			sql.append('limit')
			if isinstance(limit, int):  # limit带1个参数
				sql.append('?')
				args.append(limit)
			elif isinstance(limit, tuple) and len(limit) == 2:  # limit带2个参数
				sql.append('?, ?')
				args.extend(limit)
			else:
				raise ValueError('Invalid limit value: %s' % str(limit))
		rs = yield from select(' '.join(sql), args)  # 调用select方法，通过execute执行sql语句
		return [cls(**r) for r in rs]

	# Example: User.findNumber('count(id)')
	@classmethod
	@asyncio.coroutine
	def findNumber(cls, selectField, where=None, args=None):
		' find number by select and where. '
		sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = yield from select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']

	@classmethod
	@asyncio.coroutine
	def countRows(cls, selectField, where=None, args=None):
		' find number by select and where. '
		sql = ['select count(%s) _num_ from `%s`' % (selectField, cls.__table__)]
		if where:
			sql.append('where %s' % (where))
		resultset = yield from select(' '.join(sql), args, 1)
		if len(resultset) == 0:
			return None
		return resultset[0]['_num_']


	# Example: Blog.find(id)
	@classmethod
	@asyncio.coroutine
	def find(cls, pk):
		' find object by primary key. '
		# ?号的内容在select中实现格式输入
		rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])

	# -------------往Model类添加实例方法，就可以让所有子类调用实例方法：---------------#
	# 所有这些方法都用@asyncio.coroutine装饰，变成一个协程:

	# 保存数据
	@asyncio.coroutine
	def save(self):
		# 构建args属性值(__fields__不包括主键)list，没有的则赋值为初始默认值：
		args = list(map(self.getValueOrDefault, self.__fields__))
		# 增加主键值到args中，没有则赋值为初始默认值：
		args.append(self.getValueOrDefault(self.__primary_key__))
		# 通过实例调用 save()，把数据存入响应的对象(表)，Example: user.save()
		rows = yield from execute(self.__insert__, args)
		if rows != 1:
			logging.warn('failed to insert record: affected rows: %s' % rows)

	# 更新数据
	@asyncio.coroutine
	def update(self):
		args = list(map(self.getValue, self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows = yield from execute(self.__update__, args)
		if rows != 1:
			logging.warn('failed to update by primary key: affected rows: %s' % rows)

	# 删除数据
	@asyncio.coroutine
	def remove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = yield from execute(self.__delete__, args)
		if rows != 1:
			logging.warn('failed to remove by primary key: affected rows: %s' % rows)


if __name__ == '__main__':
	# 想定义一个User类来操作对应的数据库表User
	# 父类 Model 和属性类型 StringField、IntegerField 是由 ORM 框架提供的，剩下的
	# 魔术方法比如 save()全部由 metaclass 自动完成。
	# step3: 基于 Model 类创建 User 类。
	class User(Model):
		# 定义类的属性到列的映射：
		id = StringField(primary_key=True, ddl='varchar(50)')
		name = StringField('username')
		email = StringField('email')
		password = StringField('password')
		number = 123


	# 当用户定义一个class User(Model)时，Python解释器首先在当前类User的定义


	# 中查找metaclass，如果没有找到，就继续在父类Model中查找metaclass，找到
	# 了，就使用Model中定义的metaclass的 ModelMetaclass 来创建User类，也就是说
	# ，metaclass可以隐式地继承到子类，但子类自己却感觉不到。
	# step4: 创建一个 User 实例u：
	u = User(id=12345, name='Michael', email='test@orm.org', password='my-pwd')
	# 保存到数据库：
	# u.save()
	# print(dir(u))
