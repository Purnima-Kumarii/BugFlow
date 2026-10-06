from app.database import engine, Base
from app.models import Sprint

Base.metadata.create_all(bind=engine)

print("Sprints table created successfully!")