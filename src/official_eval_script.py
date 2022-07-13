import argparse
import os
import re
import sys
import time
from xml.etree import ElementTree

VALID_SECTION_NAMES = set(['adverse reactions', 'warnings and precautions',
                          'boxed warnings'])
VALID_MENTION_TYPES = set(['AdverseReaction', 'Severity', 'Factor', 'DrugClass',
                          'Negation', 'Animal'])
VALID_RELATION_TYPES = set(['Hypothetical', 'Effect', 'Negated'])

VALID_MENTION_OFFSETS = re.compile('^[0-9,]+$')

class Label:
  def __init__(self, drug, track):
    self.drug = drug
    self.track = track
    self.sections = []
    self.mentions = []
    self.relations = []
    self.reactions = []

class Section:
  def __init__(self, id, name, text):
    self.id = id
    self.name = name
    self.text = text

class Mention:
  def __init__(self, id, section, type, start, len, str):
    self.id = id
    self.section = section
    self.type = type
    self.start = start
    self.len = len
    self.str = str
  def __str__(self):
    return 'Mention(id={},section={},type={},start={},len={},str="{}")'.format(
        self.id, self.section, self.type, self.start, self.len, self.str)
  def __repr__(self):
    return str(self)

class Relation:
  def __init__(self, id, type, arg1, arg2):
    self.id = id
    self.type = type
    self.arg1 = arg1
    self.arg2 = arg2
  def __str__(self):
    return 'Relation(id={},type={},arg1={},arg2={})'.format(
        self.id, self.type, self.arg1, self.arg2)
  def __repr__(self):
    return str(self)

class Reaction:
  def __init__(self, id, str):
    self.id = id
    self.str = str
    self.normalizations = []

class Normalization:
  def __init__(self, id, meddra_pt, meddra_pt_id, meddra_llt, meddra_llt_id, flag):
    self.id = id
    self.meddra_pt = meddra_pt
    self.meddra_pt_id = meddra_pt_id
    self.meddra_llt = meddra_llt
    self.meddra_llt_id = meddra_llt_id
    self.flag = flag

class Results:
  def __init__(self, task1, task2, task3, task4):
    self.task1 = Task1() if task1 else None
    self.task2 = Task2() if task2 else None
    self.task3 = Task3() if task3 else None
    self.task4 = Task4() if task4 else None

class Task1:
  def __init__(self):
    self.exact_type = Classification()
    self.exact_notype = Classification()

class Task2:
  def __init__(self):
    self.full_type = Classification()
    self.full_notype = Classification()
    self.binary_type = Classification()
    self.binary_notype = Classification()

class Task3:
  def __init__(self):
    self.classifications = []

class Task4:
  def __init__(self):
    self.classifications = []

class Classification:
  def __init__(self):
    self.tp = 0
    self.tn = 0
    self.fp = 0
    self.fn = 0
  def precision(self):
    if self.tp == 0:
      return 0.0
    return 100. * self.tp / (self.tp + self.fp)
  def recall(self):
    if self.tp == 0:
      return 0.0
    return 100. * self.tp / (self.tp + self.fn)
  def f1(self):
    p, r = self.precision(), self.recall()
    if p + r == 0.0:
      return 0.0
    return 2 * p * r / (p + r)

def merge_classifications(classifications):
  classification = Classification()
  for c in classifications:
    classification.tp += c.tp
    classification.fp += c.fp
    classification.fn += c.fn
    classification.tn += c.tn
  return classification

# Returns all the XML files in a directory as a dict
def xml_files(dir):
  files = {}
  for file in os.listdir(dir):
    if file.endswith('.xml'):
      files[file.replace('.xml', '')] = os.path.join(dir, file)
  return files

# Compares the files in the two directories using compare_files
def compare_dirs(gold_dir, guess_dir, results):
  gold_files = xml_files(gold_dir)
  guess_files = xml_files(guess_dir)
  keys = sorted([x for x in gold_files if x in guess_files])
  for key in gold_files:
    if key not in keys:
      print('WARNING: gold label file not found in guess directory: ' + key)
  for key in guess_files:
    if key not in keys:
      print('WARNING: guess label file not found in gold directory: ' + key)
  for key in keys:
    #if key != 'ERWINAZE': # and key != 'EYLEA':
    #  continue
    compare_files(gold_files[key], guess_files[key], results)

# Compares the two files
def compare_files(gold_file, guess_file, results):
  #print('Evaluating: ' + os.path.basename(gold_file).replace('.xml', ''))
  gold_label = read(gold_file)
  guess_label = read(guess_file)
  validate_ind(guess_label)
  validate_ind(gold_label)
  validate_both(gold_label, guess_label)
  if results.task1 is not None:
    eval_task1(gold_label, guess_label, results)
  if results.task2:
    eval_task2(gold_label, guess_label, results)
  if results.task3:
    eval_task3(gold_label, guess_label, results)
  if results.task4:
    eval_task4(gold_label, guess_label, results)

# Reads in the XML file
def read(file):
  root = ElementTree.parse(file).getroot()
  assert root.tag == 'Label', 'Root is not Label: ' + root.tag
  label = Label(root.attrib['drug'], root.attrib['track'])
  assert len(root) == 4, 'Expected 4 Children: ' + str(list(root))
  assert root[0].tag == 'Text', 'Expected \'Text\': ' + root[0].tag
  assert root[1].tag == 'Mentions', 'Expected \'Mentions\': ' + root[0].tag
  assert root[2].tag == 'Relations', 'Expected \'Relations\': ' + root[0].tag
  assert root[3].tag == 'Reactions', 'Expected \'Reactions\': ' + root[0].tag

  for elem in root[0]:
    assert elem.tag == 'Section', 'Expected \'Section\': ' + elem.tag
    label.sections.append(
        Section(elem.attrib['id'], \
                elem.attrib['name'], \
                elem.text))

  for elem in root[1]:
    assert elem.tag == 'Mention', 'Expected \'Mention\': ' + elem.tag
    label.mentions.append(
        Mention(elem.attrib['id'], \
                elem.attrib['section'], \
                elem.attrib['type'], \
                elem.attrib['start'], \
                elem.attrib['len'], \
                attrib('str', elem)))

  for elem in root[2]:
    assert elem.tag == 'Relation', 'Expected \'Relation\': ' + elem.tag
    label.relations.append(
        Relation(elem.attrib['id'], \
                 elem.attrib['type'], \
                 elem.attrib['arg1'], \
                 elem.attrib['arg2']))

  for elem in root[3]:
    assert elem.tag == 'Reaction', 'Expected \'Reaction\': ' + elem.tag
    label.reactions.append(
        Reaction(elem.attrib['id'], elem.attrib['str']))
    for elem2 in elem:
      assert elem2.tag == 'Normalization', 'Expected \'Normalization\': ' + elem2.tag
      label.reactions[-1].normalizations.append(
          Normalization(elem2.attrib['id'], \
                        attrib('meddra_pt', elem2), \
                        attrib('meddra_pt_id', elem2), \
                        attrib('meddra_llt', elem2), \
                        attrib('meddra_llt_id', elem2), \
                        attrib('flag', elem2))) 

  return label

def attrib(name, elem):
  if name in elem.attrib:
    return elem.attrib[name]
  else:
    return None

# Validates an individual Label
def validate_ind(label):
  sections = {}
  mentions = {}
  relations = {}
  reactions = {}
  # for section in label.sections:
  #   assert section.id.startswith('S'), \
  #       'Section ID does not start with S: ' + section.id
  #   assert section.id not in sections, \
  #       'Duplicate Section ID: ' + section.id
  #   assert section.name in VALID_SECTION_NAMES, \
  #       'Invalid Section name: ' + section.name
  #   sections[section.id] = section
  # for mention in label.mentions:
  #   assert mention.id.startswith('M'), \
  #       'Mention ID does not start with M: ' + mention.id
  #   assert mention.id not in mentions, \
  #       'Duplicate Mention ID: ' + mention.id
  #   assert mention.section in sections, \
  #       'No such section in label: ' + mention.section
  #   assert VALID_MENTION_OFFSETS.match(mention.start), \
  #       'Invalid start attribute: ' + mention.start
  #   assert VALID_MENTION_OFFSETS.match(mention.len), \
  #       'Invalid len attribute: ' + mention.len
  #   assert mention.type in VALID_MENTION_TYPES, \
  #       'Invalid Mention type: ' + mention.type
  #   if mention.str is not None:
  #     mentions[mention.id] = mention
  #     text = ''
  #     for sstart, slen in zip(mention.start.split(','), mention.len.split(',')):
  #       start = int(sstart)
  #       end = start + int(slen)
  #       if len(text) > 0:
  #         text += ' '
  #       span = sections[mention.section].text[start:end]
  #       span = re.sub('\s+', ' ', span)
  #       text += span
  #     assert text == mention.str, 'Mention has wrong string value.' + \
  #         '  From \'str\': \'' + mention.str + '\'' + \
  #         '  From offsets: \'' + text + '\''
  # unique_relations = set()
  # for relation in label.relations:
  #   assert relation.id.startswith('RL'), \
  #       'Relation ID does not start with RL: ' + relation.id
  #   assert relation.id not in relations, \
  #       'Duplicate Relation ID: ' + relation.id
  #   assert relation.type in VALID_RELATION_TYPES, \
  #       'Invalid Relation type: ' + relation.type
  #   assert relation.arg1 in mentions, \
  #       'Relation ' + relation.id + ' arg1 not in mentions: ' + relation.arg1
  #   assert relation.arg2 in mentions, \
  #       'Relation ' + relation.id + ' arg2 not in mentions: ' + relation.arg2
  #   assert relation.arg1 != relation.arg2, \
  #       'Relation arguments identical (self-relation)'
  #   relation_str = relation.type + ':' + relation.arg1 + ':' + relation.arg2
  #   arg1 = mentions[relation.arg1]
  #   arg2 = mentions[relation.arg2]
  #   assert relation_str not in unique_relations, \
  #       'Duplicate Relation: ' + str(relation) + '\n' + \
  #       '  Arg1: ' + str(arg1) + '\n' + \
  #       '  Arg2: ' + str(arg2) + '\n' + \
  #       '  Label: ' + label.drug + ' ' + \
  #       str(sections[arg1.section].name)
  #   unique_relations.add(relation_str)
  #   relations[relation.id] = relation
  for reaction in label.reactions:
    assert reaction.id.startswith('AR'), \
        'Reaction ID does not start with AR: ' + reaction.id
    assert reaction.id not in reactions, \
        'Duplicate Reaction ID: ' + reaction.id
    assert reaction.str.lower() == reaction.str, \
        'Reaction str is not lower-case: ' + reaction.str
    for normalization in reaction.normalizations:
      assert normalization.id.startswith('AR'), \
          'Normalization ID does not start with AR: ' + normalization.id
      assert normalization.id.find('.N') > 0, \
          'Normalization ID does not contain .N: ' + normalization.id
      assert normalization.meddra_pt or normalization.flag == 'unmapped', \
          'Normalization does not contain meddra_pt and is not unmapped: ' + \
          label.drug + ':' + normalization.id
    reactions[reaction.id] = reaction

# Validates that the two Labels are similar enough to merit comparing
# performance metrics, mainly just comparing the sections/text to make sure
# they're identical
def validate_both(l1, l2):

  assert len(l1.sections) == len(l2.sections), \
      'Different number of sections: ' + str(len(l1.sections)) + \
      ' vs. ' + str(len(l2.sections))
  for i in range(len(l2.sections)):
    assert l1.sections[i].id == l2.sections[i].id, \
        'Different section IDs: ' + l1.sections[i].id + \
        ' vs. ' + l2.sections[i].id
    assert l1.sections[i].name == l2.sections[i].name, \
        'Different section names: ' + l1.sections[i].name + \
        ' vs. ' + l2.sections[i].name
    assert l1.sections[i].text == l2.sections[i].text, 'Different section texts'

# Evaluates Task 1 (Mentions)
def eval_task1(gold_label, guess_label, results):
  # EXACT + TYPE
  eval_f(set([exact_mention_repr(m, type=True) for m in gold_label.mentions]), \
         set([exact_mention_repr(m, type=True) for m in guess_label.mentions]), \
         results.task1.exact_type)
  # EXACT - TYPE
  eval_f(set([exact_mention_repr(m, type=False) for m in gold_label.mentions]), \
         set([exact_mention_repr(m, type=False) for m in guess_label.mentions]), \
         results.task1.exact_notype)

# Representation for exact matching of mentions
def exact_mention_repr(m, type):
  repr = m.section + ':' + m.start + ':' + m.len
  if type:
    repr += ':' + m.type
  return repr

# Evaluates Task 2 (Relations)
def eval_task2(gold_label, guess_label, results):
  gold_mentions = {m.id:m for m in gold_label.mentions}
  guess_mentions = {m.id:m for m in guess_label.mentions}
  # FULL + TYPE
  eval_f(full_relation_repr(gold_label.relations,  gold_mentions,  type=True), \
         full_relation_repr(guess_label.relations, guess_mentions, type=True), \
         results.task2.full_type)
  # FULL - TYPE
  eval_f(full_relation_repr(gold_label.relations,  gold_mentions,  type=False), \
         full_relation_repr(guess_label.relations, guess_mentions, type=False), \
         results.task2.full_notype)
  # BINARY + TYPE
  eval_f(set([binary_relation_repr(r, gold_mentions,  type=True) for r in gold_label.relations]), \
         set([binary_relation_repr(r, guess_mentions, type=True) for r in guess_label.relations]), \
         results.task2.binary_type)
  # BINARY - TYPE
  eval_f(set([binary_relation_repr(r, gold_mentions,  type=False) for r in gold_label.relations]), \
         set([binary_relation_repr(r, guess_mentions, type=False) for r in guess_label.relations]), \
         results.task2.binary_notype)

# Representation for full matching of relations
def full_relation_repr(relations, mentions, type):
  reprs = set()
  full_relations = {}
  spans = set()
  for r in relations:
    if r.arg1 not in full_relations:
      full_relations[r.arg1] = []
    arg_repr = exact_mention_repr(mentions[r.arg2], type=type)
    if type:
      arg_repr = r.type + ':' + arg_repr
    full_relations[r.arg1].append(arg_repr)
  for key, value in full_relations.items():
    repr = exact_mention_repr(mentions[key], type=type)
    spans.add(repr)
    for item in sorted(value):
      repr += '::'
      repr += item
    reprs.add(repr)
  for _, mention in mentions.items():
    repr = exact_mention_repr(mention, type=type)
    if repr in spans and mention.id not in full_relations:
      reprs.add(repr)
  return reprs

# Representation for matching of binary relations
def binary_relation_repr(relation, mentions, type):
  repr = exact_mention_repr(mentions[relation.arg1], type=type) + '::' + \
         exact_mention_repr(mentions[relation.arg2], type=type)
  if type:
    repr += '::' + relation.type
  return repr

# Evaluates Task 3 (Reactions)
def eval_task3(gold_label, guess_label, results):
  classification = Classification()
  eval_f(set([reaction_repr(r) for r in gold_label.reactions]), \
         set([reaction_repr(r) for r in guess_label.reactions]), \
         classification)
  results.task3.classifications.append(classification)

# Representation for matching reaction strings
def reaction_repr(r):
  return r.str

# Evaluates Task 4 (Normalizations)
def eval_task4(gold_label, guess_label, results):
  classification = Classification()
  eval_f(set([n for x in [norm_repr(r) for r in gold_label.reactions] for n in x]), \
         set([n for x in [norm_repr(r) for r in guess_label.reactions] for n in x]), \
         classification)
  results.task4.classifications.append(classification)

# Representation for matching reaction strings
def norm_repr(r):
  return [n.meddra_pt for n in r.normalizations if n.meddra_pt]

# Calculates statistics needed for F-measure (TP, FP, FN)
def eval_f(gold_set, guess_set, classification):
  c = {}
  for gold in gold_set:
    if gold in guess_set:
      classification.tp += 1
      assert gold not in c
      c[gold] = 'TP'
    else:
      classification.fn += 1
      assert gold not in c
      c[gold] = 'FN'
  for guess in guess_set:
    if guess not in gold_set:
      classification.fp += 1
      assert guess not in c
      c[guess] = 'FP'

# Prints various numbers related to F-measure
def print_f(name, classification, primary=False):
  print('  ' + name)
  print('    TP: {}  FP: {}  FN: {}'.format(classification.tp,
      classification.fp, classification.fn))
  print('    Precision: {:.2f}'.format(classification.precision()))
  print('    Recall:    {:.2f}'.format(classification.recall()))
  print('    F1:        {:.2f}  {}'.format(classification.f1(),
      '(PRIMARY)' if primary else ''))

# Prints various numbers related to macro F-measure
def print_macro_f(classifications):
  merge = merge_classifications(classifications)
  print('    TP: {}  FP: {}  FN: {}'.format(merge.tp,
      merge.fp, merge.fn))
  print('    Micro-Precision: {:.2f}'.format(merge.precision()))
  print('    Micro-Recall:    {:.2f}'.format(merge.recall()))
  print('    Micro-F1:        {:.2f}'.format(merge.f1()))
  print('    Macro-Precision  {:.2f}'.format(
      sum([c.precision() for c in classifications])/len(classifications)))
  print('    Macro-Recall     {:.2f}'.format(
      sum([c.recall() for c in classifications])/len(classifications)))
  print('    Macro-F1         {:.2f}  (PRIMARY)'.format(
      sum([c.f1() for c in classifications])/len(classifications)))

parser = argparse.ArgumentParser(
    description='Evaluate TAC 2017 Adverse Drug Reaction')
parser.add_argument('gold_dir', metavar='GOLD', type=str,
                    help='path to directory containing system output')
parser.add_argument('guess_dir', metavar='GUESS', type=str,
                    help='path to directory containing system output')
parser.add_argument('-1, --task1', action='store_true', dest='task1',
                    help='Evaluate Task 1')
parser.add_argument('-2, --task2', action='store_true', dest='task2',
                    help='Evaluate Task 2')
parser.add_argument('-3, --task3', action='store_true', dest='task3',
                    help='Evaluate Task 3')
parser.add_argument('-4, --task4', action='store_true', dest='task4',
                    help='Evaluate Task 4')
args = parser.parse_args()

tasks = [args.task1, args.task2, args.task3, args.task4]
if sum(tasks) == 0:
  args.task1, args.task2, args.task3, args.task4 = True, True, True, True

results = Results(args.task1, args.task2, args.task3, args.task4)

print('Gold Directory:  ' + args.gold_dir)
print('Guess Directory: ' + args.guess_dir)
compare_dirs(args.gold_dir, args.guess_dir, results)

if args.task1:
  print('--------------------------------------------------')
  print('Task 1 Results:')
  print_f('Exact (+type)', results.task1.exact_type, primary=True)
  print_f('Exact (-type)', results.task1.exact_notype)
if args.task2:
  print('--------------------------------------------------')
  print('Task 2 Results:')
  print_f('Full (+type)', results.task2.full_type, primary=True)
  print_f('Full (-type)', results.task2.full_notype)
  print_f('Binary (+type)', results.task2.binary_type)
  print_f('Binary (-type)', results.task2.binary_notype)
if args.task3:
  print('--------------------------------------------------')
  print('Task 3 Results:')
  print_macro_f(results.task3.classifications)
if args.task4:
  print('--------------------------------------------------')
  print('Task 4 Results:')
  print_macro_f(results.task4.classifications)

