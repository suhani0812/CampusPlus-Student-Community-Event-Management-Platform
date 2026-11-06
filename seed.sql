-- CampusPlus Seed Data — MIT-WPU Courses & Subjects
-- Run after schema.sql:
-- psql -U postgres -d campusplus -f seed.sql

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- COURSES
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSERT INTO courses (name, slug) VALUES
  ('B.Tech Computer Science & Engineering',               'btech-cse'),
  ('B.Tech CSE (AI & Data Science)',                      'btech-cse-aids'),
  ('B.Tech CSE (Cybersecurity & Forensics)',              'btech-cse-csf'),
  ('B.Tech CSE (Cloud Computing)',                        'btech-cse-cloud'),
  ('B.Tech Electronics & Telecommunication Engineering',  'btech-entc'),
  ('B.Tech Electrical & Electronics Engineering',         'btech-eee'),
  ('B.Tech Mechanical Engineering',                       'btech-mech'),
  ('B.Tech Civil Engineering',                            'btech-civil'),
  ('B.Tech Chemical Engineering',                         'btech-chem'),
  ('B.Tech Petroleum Engineering',                        'btech-petroleum'),
  ('B.Tech Bioengineering',                               'btech-bio'),
  ('B.Com',                                               'bcom'),
  ('BBA',                                                 'bba'),
  ('B.Sc Computer Science',                               'bsc-cs'),
  ('B.Sc Physics',                                        'bsc-physics'),
  ('B.Des',                                               'bdes'),
  ('BA Liberal Arts',                                     'ba-liberal-arts'),
  ('LLB',                                                 'llb'),
  ('MBA',                                                 'mba'),
  ('MCA',                                                 'mca'),
  ('M.Tech CSE',                                          'mtech-cse'),
  ('M.Tech AI & ML',                                      'mtech-aiml'),
  ('M.Sc Computer Science',                               'msc-cs'),
  ('M.Sc Data Science & Big Data Analytics',              'msc-ds')
ON CONFLICT (slug) DO NOTHING;


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- SUBJECTS (shared pool — no course_id)
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INSERT INTO subjects (name) VALUES
  -- Common Engineering / CS
  ('Programming Fundamentals (C & Python)'),
  ('Mathematics I (Calculus & Linear Algebra)'),
  ('Mathematics II (Discrete Mathematics)'),
  ('Mathematics II (Statistics & Probability)'),
  ('Engineering Mathematics'),
  ('Data Structures & Algorithms'),
  ('Object Oriented Programming (Java)'),
  ('Computer Organization & Architecture'),
  ('Operating Systems'),
  ('Database Management Systems'),
  ('Computer Networks'),
  ('Software Engineering'),
  ('Theory of Computation'),
  ('Compiler Design'),
  ('Artificial Intelligence'),
  ('Machine Learning'),
  ('Deep Learning'),
  ('Natural Language Processing'),
  ('Computer Vision'),
  ('Web Technologies'),
  ('Cloud Computing & DevOps'),
  ('Big Data Technologies'),
  ('Blockchain Technology'),
  ('Human Computer Interaction'),
  ('Project Management'),
  ('Peace Studies & Yoga'),
  -- AI & DS specific
  ('Data Mining & Warehousing'),
  ('AI for IoT'),
  ('Reinforcement Learning'),
  ('Cognitive Computing'),
  ('AR/VR Technologies'),
  ('Ethics in AI'),
  -- Cybersecurity specific
  ('Network Security'),
  ('Cryptography'),
  ('Ethical Hacking & Penetration Testing'),
  ('Digital Forensics'),
  ('Malware Analysis & Incident Response'),
  ('Identity & Access Management'),
  ('Enterprise Infrastructure Security'),
  ('Data Privacy & Compliance'),
  ('Cyber Laws & Cyber Crime'),
  ('Risk Assessment & Security Policies'),
  ('Vulnerability Identification'),
  -- ENTC specific
  ('Basic Electronics'),
  ('Circuit Theory'),
  ('Signals & Systems'),
  ('Digital Electronics'),
  ('Analog Electronics'),
  ('Microprocessors & Microcontrollers'),
  ('Electromagnetic Theory'),
  ('Communication Systems'),
  ('Digital Signal Processing'),
  ('VLSI Design'),
  ('Embedded Systems'),
  ('Wireless & Mobile Networks'),
  ('Antenna & Wave Propagation'),
  ('IoT & Applications'),
  -- Mechanical
  ('Engineering Drawing & Graphics'),
  ('Thermodynamics'),
  ('Fluid Mechanics'),
  ('Strength of Materials'),
  ('Manufacturing Processes'),
  ('Kinematics of Machinery'),
  ('Dynamics of Machinery'),
  ('Heat Transfer'),
  ('Machine Design'),
  ('Metrology & Quality Control'),
  ('Industrial Engineering'),
  ('Robotics & Automation'),
  ('CAD/CAM'),
  ('Finite Element Analysis'),
  -- Civil
  ('Mechanics of Structures'),
  ('Fluid Mechanics & Hydraulics'),
  ('Surveying'),
  ('Building Materials & Construction'),
  ('Structural Analysis'),
  ('Concrete Technology'),
  ('Geotechnical Engineering'),
  ('Transportation Engineering'),
  ('Environmental Engineering'),
  ('Estimation & Costing'),
  -- Petroleum
  ('Petroleum Geology'),
  ('Reservoir Engineering'),
  ('Drilling Engineering'),
  ('Well Logging'),
  ('Production Engineering'),
  ('Refinery Processes'),
  ('Petroleum Economics'),
  ('Enhanced Oil Recovery'),
  ('Natural Gas Engineering'),
  ('HSE in Oil & Gas'),
  -- Commerce / Management
  ('Financial Accounting'),
  ('Business Mathematics & Statistics'),
  ('Business Economics'),
  ('Organisational Behaviour'),
  ('Corporate Law'),
  ('Cost Accounting'),
  ('Income Tax'),
  ('Auditing'),
  ('Financial Management'),
  ('Marketing Management'),
  ('Business Communication'),
  ('E-Commerce'),
  ('Entrepreneurship Development'),
  ('Peace Studies'),
  ('Principles of Management'),
  ('Human Resource Management'),
  ('Operations Management'),
  ('Business Law'),
  ('Entrepreneurship'),
  ('Strategic Management'),
  ('International Business'),
  ('Business Analytics'),
  -- MBA extra
  ('Operations & Supply Chain Management'),
  ('Business Research Methods'),
  ('Corporate Governance & Ethics'),
  ('Entrepreneurship & Innovation'),
  ('Business Analytics & Data Visualisation'),
  -- MCA extra
  ('Mobile Application Development'),
  ('Cyber Security')
ON CONFLICT (name) DO NOTHING;


-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- COURSE–SUBJECT LINKS
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- Helper: link subjects to a course by slug and subject names
-- B.Tech CSE
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'btech-cse' AND s.name IN (
  'Programming Fundamentals (C & Python)',
  'Mathematics I (Calculus & Linear Algebra)',
  'Mathematics II (Discrete Mathematics)',
  'Data Structures & Algorithms',
  'Object Oriented Programming (Java)',
  'Computer Organization & Architecture',
  'Operating Systems',
  'Database Management Systems',
  'Computer Networks',
  'Software Engineering',
  'Theory of Computation',
  'Compiler Design',
  'Artificial Intelligence',
  'Machine Learning',
  'Web Technologies',
  'Information & Cyber Security',
  'Cloud Computing & DevOps',
  'Big Data Technologies',
  'Deep Learning',
  'Computer Vision',
  'Blockchain Technology',
  'Human Computer Interaction',
  'Project Management',
  'Peace Studies & Yoga'
) ON CONFLICT DO NOTHING;

-- B.Tech CSE (AI & Data Science)
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'btech-cse-aids' AND s.name IN (
  'Programming Fundamentals (C & Python)',
  'Mathematics I (Calculus & Linear Algebra)',
  'Mathematics II (Statistics & Probability)',
  'Data Structures & Algorithms',
  'Database Management Systems',
  'Machine Learning',
  'Deep Learning',
  'Natural Language Processing',
  'Computer Vision',
  'Big Data Technologies',
  'Data Mining & Warehousing',
  'AI for IoT',
  'Reinforcement Learning',
  'Cognitive Computing',
  'AR/VR Technologies',
  'Cloud Computing & DevOps',
  'Ethics in AI',
  'Peace Studies & Yoga'
) ON CONFLICT DO NOTHING;

-- B.Tech CSE (Cybersecurity & Forensics)
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'btech-cse-csf' AND s.name IN (
  'Programming Fundamentals (C & Python)',
  'Mathematics I (Calculus & Linear Algebra)',
  'Data Structures & Algorithms',
  'Operating Systems',
  'Computer Networks',
  'Network Security',
  'Cryptography',
  'Ethical Hacking & Penetration Testing',
  'Digital Forensics',
  'Malware Analysis & Incident Response',
  'Identity & Access Management',
  'Enterprise Infrastructure Security',
  'Data Privacy & Compliance',
  'Cyber Laws & Cyber Crime',
  'Risk Assessment & Security Policies',
  'Vulnerability Identification',
  'Peace Studies & Yoga'
) ON CONFLICT DO NOTHING;

-- B.Tech CSE (Cloud Computing)
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'btech-cse-cloud' AND s.name IN (
  'Programming Fundamentals (C & Python)',
  'Mathematics I (Calculus & Linear Algebra)',
  'Data Structures & Algorithms',
  'Operating Systems',
  'Computer Networks',
  'Database Management Systems',
  'Cloud Computing & DevOps',
  'Software Engineering',
  'Web Technologies',
  'Big Data Technologies',
  'Cyber Security',
  'AI for IoT',
  'Peace Studies & Yoga'
) ON CONFLICT DO NOTHING;

-- B.Tech ENTC
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'btech-entc' AND s.name IN (
  'Mathematics I (Calculus & Linear Algebra)',
  'Mathematics II (Discrete Mathematics)',
  'Basic Electronics',
  'Circuit Theory',
  'Signals & Systems',
  'Digital Electronics',
  'Analog Electronics',
  'Microprocessors & Microcontrollers',
  'Electromagnetic Theory',
  'Communication Systems',
  'Digital Signal Processing',
  'VLSI Design',
  'Embedded Systems',
  'Wireless & Mobile Networks',
  'Antenna & Wave Propagation',
  'IoT & Applications',
  'Peace Studies & Yoga'
) ON CONFLICT DO NOTHING;

-- B.Tech Mechanical
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'btech-mech' AND s.name IN (
  'Engineering Mathematics',
  'Engineering Drawing & Graphics',
  'Thermodynamics',
  'Fluid Mechanics',
  'Strength of Materials',
  'Manufacturing Processes',
  'Kinematics of Machinery',
  'Dynamics of Machinery',
  'Heat Transfer',
  'Machine Design',
  'Metrology & Quality Control',
  'Industrial Engineering',
  'Robotics & Automation',
  'CAD/CAM',
  'Finite Element Analysis',
  'Peace Studies & Yoga'
) ON CONFLICT DO NOTHING;

-- B.Tech Civil
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'btech-civil' AND s.name IN (
  'Engineering Mathematics',
  'Engineering Drawing & Graphics',
  'Mechanics of Structures',
  'Fluid Mechanics & Hydraulics',
  'Surveying',
  'Building Materials & Construction',
  'Structural Analysis',
  'Concrete Technology',
  'Geotechnical Engineering',
  'Transportation Engineering',
  'Environmental Engineering',
  'Estimation & Costing',
  'Project Management',
  'Peace Studies & Yoga'
) ON CONFLICT DO NOTHING;

-- B.Tech Petroleum
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'btech-petroleum' AND s.name IN (
  'Engineering Mathematics',
  'Petroleum Geology',
  'Fluid Mechanics',
  'Reservoir Engineering',
  'Drilling Engineering',
  'Well Logging',
  'Production Engineering',
  'Refinery Processes',
  'Petroleum Economics',
  'Enhanced Oil Recovery',
  'Natural Gas Engineering',
  'HSE in Oil & Gas',
  'Peace Studies & Yoga'
) ON CONFLICT DO NOTHING;

-- B.Com
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'bcom' AND s.name IN (
  'Financial Accounting',
  'Business Mathematics & Statistics',
  'Business Economics',
  'Organisational Behaviour',
  'Corporate Law',
  'Cost Accounting',
  'Income Tax',
  'Auditing',
  'Financial Management',
  'Marketing Management',
  'Business Communication',
  'E-Commerce',
  'Entrepreneurship Development',
  'Peace Studies'
) ON CONFLICT DO NOTHING;

-- BBA
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'bba' AND s.name IN (
  'Principles of Management',
  'Business Communication',
  'Financial Accounting',
  'Business Economics',
  'Marketing Management',
  'Human Resource Management',
  'Operations Management',
  'Business Law',
  'Entrepreneurship',
  'Strategic Management',
  'International Business',
  'Business Analytics',
  'Peace Studies'
) ON CONFLICT DO NOTHING;

-- MBA
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'mba' AND s.name IN (
  'Business Economics',
  'Financial Management',
  'Marketing Management',
  'Human Resource Management',
  'Operations & Supply Chain Management',
  'Business Research Methods',
  'Organisational Behaviour',
  'Strategic Management',
  'Business Analytics & Data Visualisation',
  'Corporate Governance & Ethics',
  'Entrepreneurship & Innovation',
  'International Business',
  'Peace Studies'
) ON CONFLICT DO NOTHING;

-- MCA
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'mca' AND s.name IN (
  'Data Structures & Algorithms',
  'Object Oriented Programming (Java)',
  'Database Management Systems',
  'Operating Systems',
  'Computer Networks',
  'Software Engineering',
  'Web Technologies',
  'Cloud Computing & DevOps',
  'Machine Learning',
  'Mobile Application Development',
  'Cyber Security',
  'Project Management'
) ON CONFLICT DO NOTHING;

-- M.Tech CSE
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'mtech-cse' AND s.name IN (
  'Machine Learning',
  'Deep Learning',
  'Computer Vision',
  'Natural Language Processing',
  'Cloud Computing & DevOps',
  'Big Data Technologies',
  'Compiler Design',
  'Theory of Computation',
  'Software Engineering',
  'Research Methodology'
) ON CONFLICT DO NOTHING;

-- M.Tech AI & ML
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'mtech-aiml' AND s.name IN (
  'Machine Learning',
  'Deep Learning',
  'Natural Language Processing',
  'Computer Vision',
  'Reinforcement Learning',
  'Cognitive Computing',
  'Big Data Technologies',
  'AI for IoT',
  'Ethics in AI'
) ON CONFLICT DO NOTHING;

-- M.Sc Computer Science
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'msc-cs' AND s.name IN (
  'Data Structures & Algorithms',
  'Operating Systems',
  'Computer Networks',
  'Database Management Systems',
  'Artificial Intelligence',
  'Machine Learning',
  'Web Technologies',
  'Cyber Security',
  'Cloud Computing & DevOps',
  'Software Engineering'
) ON CONFLICT DO NOTHING;

-- M.Sc Data Science
INSERT INTO course_subjects (course_id, subject_id)
SELECT c.id, s.id FROM courses c, subjects s
WHERE c.slug = 'msc-ds' AND s.name IN (
  'Machine Learning',
  'Deep Learning',
  'Data Mining & Warehousing',
  'Big Data Technologies',
  'Natural Language Processing',
  'Computer Vision',
  'Reinforcement Learning',
  'Business Analytics & Data Visualisation',
  'Mathematics II (Statistics & Probability)',
  'Ethics in AI'
) ON CONFLICT DO NOTHING;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- CLUBS (sourced from mitwpu.edu.in/life-wpu/clubs)
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSERT INTO clubs (name, category, description, instagram_handle, apply_link) VALUES
 
  ('Cultural Club (Theatre)', 'cultural',
   'One of the oldest clubs at MIT-WPU, established in 1983. Nurtures creativity and promotes artistic expression through theatre, drama, workshops, and state/national level competitions.',
   '@mitwpu_cultural', 'https://mitwpu.edu.in/mit-wpu-cultural-club'),
 
  ('Nisargvedh (Adventure Club)', 'sports',
   'MIT-WPU''s adventure club, partnered with Giripremi Adventure Foundation. Focuses on trekking, outdoor exploration, and adventure sports. Inaugurated on National Youth Day 2023.',
   NULL, 'https://mitwpu.edu.in/life-wpu/adventure-club/about-adventure-club'),
 
  ('INIT Cloud Club', 'technical',
   'Dedicated to cloud computing enthusiasts. Organises coding competitions, meetups, community-driven projects, and industry-level networking events focused on cloud technologies.',
   NULL, 'https://mitwpu.edu.in/init-cloud-club'),
 
  ('ACM Club', 'technical',
   'MIT-WPU''s Association for Computing Machinery student chapter. Focused on empowering women in technology, knowledge sharing, and creating opportunities for personal and professional growth in tech.',
   NULL, 'https://mitwpu.edu.in/acm-club'),
 
  ('Nummerates Club', 'technical',
   'A student-driven club dedicated to mathematical innovation and academic excellence. Mentors projects, conducts workshops on advanced mathematical concepts, and hosts speaker sessions for technical interviews.',
   NULL, 'https://mitwpu.edu.in/nummerates-club'),
 
  ('Innovation Hub', 'innovation',
   'MIT-WPU''s flagship innovation club. Hosts Launchpad, Connect, NASA Space Apps Challenge, HACK MIT, R.I.D.E (startup fair), and Inception. Runs bootcamps and workshops for hardware and software skills.',
   NULL, 'https://mitwpu.edu.in/innovation-clubs/innovation-hub'),
 
  ('UMED Social Club', 'social',
   'Established in 2022 under the School of Commerce. Focuses on raising awareness about social issues through documentaries, community outreach, and visits to orphanages and NGOs.',
   NULL, 'https://mitwpu.edu.in/umed-social-club'),
 
  ('Cosmos Astronomy Club', 'technical',
   'Open to anyone with an interest in astronomy and the scientific process, including beginners. Organises stargazing sessions, talks, and science activities.',
   NULL, NULL),
 
  ('Business Incubator Club', 'innovation',
   'Supports students who want to launch startups by helping them bootstrap ideas, make products viable, and connect with MIT-WPU''s Technology Business Incubator (MIT-TBI).',
   NULL, NULL),
 
  ('Young Democrats Club', 'social',
   'A platform for students interested in politics, governance, public policy, and democratic values. Organises debates, discussions, and civic engagement activities.',
   NULL, NULL),
 
  ('Research Nexus Forum', 'technical',
   'Promotes a strong research culture through student-faculty collaboration, mentoring, and interdisciplinary inquiry. Enables high-quality research, publications, and industry-linked studies.',
   NULL, NULL),
 
  ('Niramay Club', 'cultural',
   'The socio-cultural platform of the Ramcharan School of Leadership. Nurtures cultural expression, community engagement, mental well-being, and values-based leadership.',
   NULL, NULL)
 
ON CONFLICT (name) DO NOTHING;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- ADMIN USER
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 
-- Insert admin user (bypasses OTP — seeded directly)
INSERT INTO users (email, password_hash, is_verified, full_name, created_at)
VALUES (
    'campusplus76@gmail.com',
    '489353c0f77bb4e22f6ad8fd79433add04f93912b8e8f436dbb428dc1c8191ac',
    TRUE,
    'CampusPlus Admin',
    NOW()
) ON CONFLICT (email) DO NOTHING;
 
-- Assign admin role (trigger assigns student, we add admin separately)
INSERT INTO user_roles (user_id, role, assigned_at)
SELECT id, 'admin', NOW()
FROM users
WHERE email = 'campusplus76@gmail.com'
ON CONFLICT DO NOTHING;
 