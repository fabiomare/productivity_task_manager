from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional

# FastAPI instance
app = FastAPI()

# Path to the templates directory
templates = Jinja2Templates(directory="templates")

# SQLite Database setup using SQLAlchemy
DATABASE_URL = "sqlite:///./todos.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy model for database
class TodoItem(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    priority = Column(Integer, index=True)
    done = Column(Boolean, default=False)  # Track if the task is done

# Create the database tables if they don't exist
Base.metadata.create_all(bind=engine)

# Pydantic model for validation (used when creating a Todo)
class TodoCreate(BaseModel):
    title: str
    description: str
    priority: int

    class Config:
        from_attributes = True  # Pydantic V2: renaming orm_mode to from_attributes

# Pydantic model for serialization and validation when retrieving a Todo item
class TodoItemResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    priority: Optional[int] = None
    done: bool = False

    class Config:
        from_attributes = True  # Pydantic V2: renaming orm_mode to from_attributes

# Dependency to get DB session
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Routes

# Root route to render the landing page (index_root.html)
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index_root.html", {"request": request})

# Route to display the todo list (index_todos.html)
@app.get("/todos/", response_class=HTMLResponse)
async def todos(request: Request, db: Session = Depends(get_db)):
    # Fetch all todos from the database ordered by priority and filter by done status
    active_todos = db.query(TodoItem).filter(TodoItem.done == False).order_by(TodoItem.priority).all()
    done_todos = db.query(TodoItem).filter(TodoItem.done == True).all()
    return templates.TemplateResponse("index_todos.html", {"request": request, "active_todos": active_todos, "done_todos": done_todos})

# 1. Create a new to-do item
@app.post("/todos/", response_model=TodoItemResponse)
def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
    new_todo = TodoItem(**todo.dict())
    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)
    return new_todo  # Return the created TodoItem as response

# 2. Mark a to-do item as done
@app.put("/todos/{todo_id}/done", response_model=TodoItemResponse)
def mark_done(todo_id: int, db: Session = Depends(get_db)):
    todo_item = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo_item:
        raise HTTPException(status_code=404, detail="To-do not found")
    todo_item.done = True
    db.commit()
    db.refresh(todo_item)
    return todo_item

# 3. Retrieve all to-do items as JSON (for API purposes)
@app.get("/api/todos/", response_model=List[TodoItemResponse])
def get_todos_api(db: Session = Depends(get_db)):
    try:
        todos = db.query(TodoItem).all()
        return todos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving todos: {e}")

# 4. Update a to-do item by ID
@app.put("/todos/{todo_id}", response_model=TodoItemResponse)
def update_todo(todo_id: int, todo: TodoCreate, db: Session = Depends(get_db)):
    todo_item = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo_item:
        raise HTTPException(status_code=404, detail="To-do not found")
    for key, value in todo.dict().items():
        setattr(todo_item, key, value)
    db.commit()
    db.refresh(todo_item)
    return todo_item

# 5. Delete a to-do item by ID
@app.delete("/todos/{todo_id}", response_model=dict)
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    todo_item = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo_item:
        raise HTTPException(status_code=404, detail="To-do not found")
    db.delete(todo_item)
    db.commit()
    return {"message": "To-do deleted successfully"}
