import tempfile,unittest
from backend.generate import generate
class TestGenerator(unittest.TestCase):
 def test_reproducible(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   x=generate(a,30,4,60,400);y=generate(b,30,4,60,400)
   self.assertEqual(x['sha256'],y['sha256']);self.assertEqual(x['foreign_key_errors'],0)
   self.assertEqual(x['counts']['activity_event'],400)
if __name__=='__main__':unittest.main()
