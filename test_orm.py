from orm import Model, IntegerField, StringField
from models import Blog


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

# 当用户定义一个class User(Model)时，Python解释器首先在当前类User的定义


# 中查找metaclass，如果没有找到，就继续在父类Model中查找metaclass，找到
# 了，就使用Model中定义的metaclass的 ModelMetaclass 来创建User类，也就是说
# ，metaclass可以隐式地继承到子类，但子类自己却感觉不到。
# step4: 创建一个 User 实例u：
u = User(id=12345, name='Michael', email='test@orm.org', password='my-pwd')
# # 保存到数据库：
u.save()
print(dir(u))
# ['__class__', '__contains__', '__delattr__', '__delitem__', '__dict__', '__dir__
# ', '__doc__', '__eq__', '__format__', '__ge__', '__getattr__', '__getattribute__
# ', '__getitem__', '__gt__', '__hash__', '__init__', '__iter__', '__le__', '__len
# __', '__lt__', '__mappings__', '__module__', '__ne__', '__new__', '__reduce__',
# '__reduce_ex__', '__repr__', '__setattr__', '__setitem__', '__sizeof__', '__str_
# _', '__subclasshook__', '__table__', '__weakref__', 'clear', 'copy', 'fromkeys',
#  'get', 'items', 'keys', 'pop', 'popitem', 'save', 'setdefault', 'update', 'valu
# es']


