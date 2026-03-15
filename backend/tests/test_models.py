from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Profile

def test_profile_table_exists():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    p = Profile(id=1, name="Jane Doe", email="jane@example.com")
    db.add(p)
    db.commit()
    result = db.query(Profile).filter_by(id=1).first()
    assert result.name == "Jane Doe"
    assert result.work_experience == "[]"
    db.close()
