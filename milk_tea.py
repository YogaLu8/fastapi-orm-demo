from fastapi import FastAPI
from sqlalchemy import create_engine

app = FastAPI(title= "奶茶店业务")

engine = create_engine("mysql+pymysql://root:你的密码@localhost:3306/milk_tea_db?charset=utf8mb4", echo = True)


from sqlalchemy.orm import DeclarativeBase,mapped_column, Mapped
class Base(DeclarativeBase):
    pass

from sqlalchemy import String, Numeric
class Drinks(Base):
    __tablename__ = "drinks"
    id: Mapped[int] = mapped_column(primary_key= True, autoincrement= True)
    name: Mapped[str] = mapped_column(String(10), nullable=False, unique= True)
    price: Mapped[float] = mapped_column(Numeric(10,2), nullable=False)
    stock: Mapped[int] = mapped_column(nullable=False)

from sqlalchemy import ForeignKey
class Orders(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key= True, autoincrement= True)
    drink_id: Mapped[int] = mapped_column(ForeignKey("drinks.id"))
    buyer: Mapped[str] = mapped_column(String(10), nullable=False)
    num: Mapped[int] = mapped_column(nullable=False, default=1)

Base.metadata.create_all(engine)

from sqlalchemy.orm import sessionmaker
SessionLocal = sessionmaker(bind=engine)

from fastapi import status
@app.get("/", summary = "根路径", status_code= status.HTTP_200_OK)
async def root():
    return {"msg": "登录成功!欢迎来到奶茶店"}

from pydantic import BaseModel, Field
from typing import Annotated
class CreateDrink(BaseModel):
    name: Annotated[str, Field(min_length=4, max_length=10, description="饮品名称")]
    price: Annotated[float, Field(gt=0, description="饮品价格")]
    stock: Annotated[int, Field(ge=0, description="库存数量")]

class CreateOrder(BaseModel):
    drink_id: Annotated[int, Field(gt=0, description="饮品ID")]
    buyer: Annotated[str, Field(min_length=2, max_length=10, description="买家名称")]
    num: Annotated[int, Field(ge=1, description="购买数量")]

@app.post("/drink", tags = ["饮品"], summary = "添加饮品", status_code= status.HTTP_201_CREATED)
async def add_drinks(drink: CreateDrink):
    db = SessionLocal()
    try:
        new_drink = Drinks(**drink.model_dump())
        db.add(new_drink)
        db.commit()
        db.refresh(new_drink)
        return {"msg": "饮品添加成功", "drink": drink.model_dump()}

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

from fastapi import Path,HTTPException
from sqlalchemy import select
@app.get("/drink/{drink_id}", tags= ["饮品"], summary= "查询单个饮品", status_code= status.HTTP_200_OK)
async def drinks(drink_id: Annotated[int, Path(ge = 0)]):
    db = SessionLocal()
    try:
         stmt = select(Drinks).where(Drinks.id == drink_id)
         result = db.scalar(stmt)
         if not result:
             raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail = "饮品id不存在")
         else:
            return {"msg": "查询成功", "drink": result}
    finally:
        db.close()

@app.get("/drink", tags= ["饮品"], summary= "查询所有饮品", status_code= status.HTTP_200_OK)
async def all_drinks():
    db = SessionLocal()
    try:
        stmts = select(Drinks)
        results = db.scalars(stmts).all()
        return {"msg": "查询成功", "drink": results}
    finally:
        db.close()

@app.post("/order", tags= ["订单"], summary= "创建订单", status_code= status.HTTP_201_CREATED)
async def create_order(order: CreateOrder):
    db = SessionLocal()
    try:
        new_order = Orders(**order.model_dump())
        stmt = select(Drinks).where(Drinks.id == order.drink_id)
        drink_result = db.scalar(stmt)
        if not drink_result:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail = "饮品id不存在")
        else:
            if order.num > drink_result.stock:
                raise HTTPException(status_code= status.HTTP_400_BAD_REQUEST, detail = "库存不足")

        db.add(new_order)
        drink_result.stock -= order.num
        db.commit()
        db.refresh(new_order)
        return {"msg": "添加成功", "order": new_order}
    finally:
        db.close()

@app.get("/order/{order_id}", tags= ["订单"], summary= "查询订单详情", status_code= status.HTTP_200_OK)
async def order(order_id: Annotated[int, Path(gt= 0)]):
    db = SessionLocal()
    try:
        order_stmt = select(Orders).where(Orders.id == order_id)
        result = db.scalar(order_stmt)
        if not result:
            raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail = "订单id不存在")
        else:
            drink_stmt = select(Drinks).where(Drinks.id == result.drink_id)
            drinks_result = db.scalar(drink_stmt)
            if not drinks_result:
                raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail = "饮品id不存在")
            return {"msg": "查询成功", "buyer": result.buyer, "drink": drinks_result.name, "num": result.num}
    finally:
        db.close()

@app.get("/order", tags= ["订单"], summary= "查询所有订单", status_code= status.HTTP_200_OK)
async def all_orders():
    db = SessionLocal()
    try:
        stmts = select(Orders)
        results = db.scalars(stmts).all()
        return {"msg": "查询成功", "orders": results}
    finally:
        db.close()
