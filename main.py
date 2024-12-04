from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
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

# SQLAlchemy models for database
class TodoItem(Base):
    __tablename__ = "todos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, index=True)
    priority = Column(Integer, index=True)
    done = Column(Boolean, default=False)  # Track if the task is done
    estimated_hours = Column(Integer, nullable=True)  # Estimated hours for completion
    subtasks = relationship("Subtask", back_populates="parent_task", cascade="all, delete-orphan")

# Updated SQLAlchemy Models
class Subtask(Base):
    __tablename__ = "subtasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    done = Column(Boolean, default=False)
    estimated_hours = Column(Integer, nullable=True)  # Add estimated hours to subtasks
    task_id = Column(Integer, ForeignKey("todos.id"))
    parent_task = relationship("TodoItem", back_populates="subtasks")

# Create the database tables if they don't exist
Base.metadata.create_all(bind=engine)

class SubtaskCreate(BaseModel):
    title: str
    estimated_hours: Optional[int]  # Ensure hours are included

    class Config:
        from_attributes = True


class SubtaskResponse(BaseModel):
    id: int
    title: str
    done: bool

    class Config:
        from_attributes = True

class TodoCreate(BaseModel):
    title: str
    description: str
    priority: int
    estimated_hours: Optional[int] = None
    subtasks: Optional[List[SubtaskCreate]] = []

    class Config:
        from_attributes = True

class TodoItemResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    priority: Optional[int] = None
    done: bool = False
    estimated_hours: Optional[int] = None
    subtasks: List[SubtaskResponse] = []

    class Config:
        from_attributes = True

# Dependency to get DB session
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Routes
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index_root.html", {"request": request})

@app.get("/todos/", response_class=HTMLResponse)
async def todos(request: Request, db: Session = Depends(get_db)):
    active_todos = db.query(TodoItem).filter(TodoItem.done == False).order_by(TodoItem.priority).all()
    done_todos = db.query(TodoItem).filter(TodoItem.done == True).all()

    # Debugging log to check the data fetched
    print("Active Todos:", active_todos)
    print("Done Todos:", done_todos)

    return templates.TemplateResponse(
        "index_todos.html",
        {"request": request, "active_todos": active_todos, "done_todos": done_todos},
    )


@app.post("/todos/", response_model=TodoItemResponse)
def create_todo(todo: TodoCreate, db: Session = Depends(get_db)):
    print("Incoming Todo Data:", todo.dict())  # Debugging log
    try:
        new_todo = TodoItem(
            title=todo.title,
            description=todo.description,
            priority=todo.priority,
        )
        db.add(new_todo)
        db.flush()  # Persist new task to assign subtasks

        # Process subtasks
        for subtask in todo.subtasks:
            print("Processing Subtask:", subtask)  # Debugging log
            new_subtask = Subtask(
                title=subtask.title,
                estimated_hours=subtask.estimated_hours,
                parent_task=new_todo,
            )
            db.add(new_subtask)

        db.commit()
        db.refresh(new_todo)
        update_task_hours(new_todo, db)
        return new_todo
    except Exception as e:
        print("Error Creating Todo:", str(e))  # Log the error
        raise HTTPException(status_code=400, detail=f"Error creating task: {str(e)}")


@app.put("/todos/{todo_id}", response_model=TodoItemResponse)
def update_todo(todo_id: int, todo: TodoCreate, db: Session = Depends(get_db)):
    todo_item = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo_item:
        raise HTTPException(status_code=404, detail="To-do not found")
    todo_item.title = todo.title
    todo_item.description = todo.description
    todo_item.priority = todo.priority
    todo_item.estimated_hours = todo.estimated_hours
    # Update subtasks
    existing_subtasks = {subtask.id: subtask for subtask in todo_item.subtasks}
    for subtask in todo.subtasks:
        if subtask.id in existing_subtasks:
            existing_subtasks[subtask.id].title = subtask.title
        else:
            new_subtask = Subtask(title=subtask.title, parent_task=todo_item)
            db.add(new_subtask)
    db.commit()
    db.refresh(todo_item)
    return todo_item

@app.put("/todos/{todo_id}/done", response_model=TodoItemResponse)
def mark_done(todo_id: int, db: Session = Depends(get_db)):
    todo_item = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo_item:
        raise HTTPException(status_code=404, detail="To-do not found")
    todo_item.done = True
    # Mark all subtasks as done
    for subtask in todo_item.subtasks:
        subtask.done = True
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

@app.put("/todos/{todo_id}", response_model=TodoItemResponse)
def update_todo(todo_id: int, todo: TodoCreate, db: Session = Depends(get_db)):
    todo_item = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo_item:
        raise HTTPException(status_code=404, detail="To-do not found")

    todo_item.title = todo.title
    todo_item.description = todo.description
    todo_item.priority = todo.priority

    # Update subtasks
    existing_subtasks = {subtask.id: subtask for subtask in todo_item.subtasks}
    for subtask in todo.subtasks:
        if subtask.id in existing_subtasks:
            existing_subtasks[subtask.id].title = subtask.title
            existing_subtasks[subtask.id].estimated_hours = subtask.estimated_hours
        else:
            new_subtask = Subtask(
                title=subtask.title, 
                estimated_hours=subtask.estimated_hours, 
                parent_task=todo_item
            )
            db.add(new_subtask)
    db.commit()
    update_task_hours(todo_item, db)
    db.refresh(todo_item)
    return todo_item

# Utility Function to Recalculate Task Hours
def update_task_hours(task: TodoItem, db: Session):
    task.estimated_hours = sum(subtask.estimated_hours or 0 for subtask in task.subtasks)
    db.commit()

# 5. Delete a to-do item by ID
@app.delete("/todos/{todo_id}", response_model=dict)
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    todo_item = db.query(TodoItem).filter(TodoItem.id == todo_id).first()
    if not todo_item:
        raise HTTPException(status_code=404, detail="To-do not found")

    # Automatically delete subtasks due to cascade="all, delete-orphan"
    db.delete(todo_item)
    db.commit()
    return {"message": "To-do deleted successfully"}
