 
# company_resume_optimizer.py

import re
import json
from datetime import datetime

class CompanyResumeOptimizer:
    """Company-specific resume optimization engine"""
    
    def __init__(self):
        self.company_requirements = {
            'TCS': {
                'keywords': ['java', 'sql', 'communication', 'aptitude', 'teamwork', 'problem solving', 'agile'],
                'priority_skills': ['java', 'sql', 'spring boot', 'hibernate', 'html', 'css', 'javascript'],
                'projects': ['Inventory Management', 'Employee Management', 'E-commerce Website', 'Banking System'],
                'certifications': ['Java Certification', 'SQL Certification', 'TCS iON Certification'],
                'action_verbs': ['developed', 'implemented', 'designed', 'maintained', 'collaborated'],
                'resume_tips': ['Highlight teamwork', 'Show problem-solving skills', 'Include academic projects'],
                'min_ats_score': 70
            },
            'Infosys': {
                'keywords': ['python', 'java', 'sql', 'system design', 'agile', 'scrum', 'microservices'],
                'priority_skills': ['python', 'java', 'django', 'flask', 'mongodb', 'mysql', 'rest api'],
                'projects': ['Web Application', 'API Development', 'Database System', 'Cloud Application'],
                'certifications': ['Python Certification', 'Full Stack Development', 'Infosys Certification'],
                'action_verbs': ['architected', 'built', 'created', 'optimized', 'scaled'],
                'resume_tips': ['Focus on scalable solutions', 'Highlight system design', 'Show learning agility'],
                'min_ats_score': 75
            },
            'Wipro': {
                'keywords': ['c++', 'java', 'sql', 'communication', 'leadership', 'project management'],
                'priority_skills': ['c++', 'java', 'oracle', 'mysql', 'html', 'css', 'javascript'],
                'projects': ['Desktop Application', 'Database Project', 'Team Project', 'Client Management'],
                'certifications': ['C++ Certification', 'Project Management', 'Wipro Certification'],
                'action_verbs': ['managed', 'coordinated', 'executed', 'delivered', 'achieved'],
                'resume_tips': ['Highlight leadership', 'Show project management', 'Include team achievements'],
                'min_ats_score': 70
            },
            'Accenture': {
                'keywords': ['cloud', 'aws', 'azure', 'ai', 'ml', 'digital', 'innovation', 'consulting'],
                'priority_skills': ['aws', 'azure', 'python', 'java', 'docker', 'kubernetes', 'jenkins'],
                'projects': ['Cloud Migration', 'AI Solution', 'Digital Transformation', 'Consulting Project'],
                'certifications': ['AWS Certified', 'Azure Certified', 'AI Certification', 'Cloud Certification'],
                'action_verbs': ['transformed', 'innovated', 'modernized', 'accelerated', 'optimized'],
                'resume_tips': ['Show digital mindset', 'Highlight innovation', 'Include cloud experience'],
                'min_ats_score': 75
            },
            'Cognizant': {
                'keywords': ['digital', 'automation', 'ai', 'data analytics', 'cloud', 'cybersecurity'],
                'priority_skills': ['python', 'java', 'data analysis', 'tableau', 'power bi', 'sql'],
                'projects': ['Data Analytics', 'Automation Tool', 'Digital Solution', 'Business Intelligence'],
                'certifications': ['Data Analytics', 'AI Certification', 'Digital Transformation'],
                'action_verbs': ['analyzed', 'automated', 'digitized', 'streamlined', 'enhanced'],
                'resume_tips': ['Focus on digital skills', 'Show data expertise', 'Highlight automation'],
                'min_ats_score': 70
            },
            'Google': {
                'keywords': ['data structures', 'algorithms', 'system design', 'python', 'java', 'go', 'scalability'],
                'priority_skills': ['python', 'java', 'go', 'c++', 'distributed systems', 'machine learning', 'tensorflow'],
                'projects': ['Search Engine', 'Recommendation System', 'Large Scale Application', 'ML Model'],
                'certifications': ['Google Cloud Certified', 'ML Certification', 'System Design'],
                'action_verbs': ['engineered', 'architected', 'revolutionized', 'optimized', 'scaled'],
                'resume_tips': ['Focus on algorithms', 'Show scalability', 'Highlight impact metrics'],
                'min_ats_score': 85
            },
            'Amazon': {
                'keywords': ['customer obsession', 'ownership', 'scalability', 'aws', 'distributed systems', 'frugality'],
                'priority_skills': ['aws', 'java', 'python', 'distributed systems', 'database', 'microservices'],
                'projects': ['E-commerce Platform', 'Cloud Native App', 'Scalable Service', 'Inventory System'],
                'certifications': ['AWS Certified Solutions Architect', 'Cloud Computing', 'Scalability'],
                'action_verbs': ['delivered', 'owned', 'scaled', 'optimized', 'launched'],
                'resume_tips': ['Show customer focus', 'Highlight ownership', 'Include metrics'],
                'min_ats_score': 85
            },
            'Microsoft': {
                'keywords': ['azure', 'c#', '.net', 'cloud', 'ai', 'innovation', 'growth mindset'],
                'priority_skills': ['c#', '.net', 'azure', 'python', 'typescript', 'react', 'sql server'],
                'projects': ['Cloud Application', 'AI Solution', 'Windows App', 'Enterprise Software'],
                'certifications': ['Microsoft Certified: Azure Developer', '.NET Certification', 'AI Certification'],
                'action_verbs': ['innovated', 'transformed', 'modernized', 'built', 'created'],
                'resume_tips': ['Show growth mindset', 'Highlight innovation', 'Include cloud experience'],
                'min_ats_score': 80
            },
            'Meta': {
                'keywords': ['social media', 'scale', 'react', 'php', 'python', 'distributed systems', 'move fast'],
                'priority_skills': ['react', 'php', 'python', 'graphql', 'android', 'ios', 'c++'],
                'projects': ['Social Platform', 'Mobile App', 'Real-time System', 'Large Scale Service'],
                'certifications': ['React Certification', 'Mobile Development', 'System Design'],
                'action_verbs': ['accelerated', 'shipped', 'launched', 'scaled', 'innovated'],
                'resume_tips': ['Show impact metrics', 'Highlight speed', 'Include scale'],
                'min_ats_score': 85
            },
            'Adobe': {
                'keywords': ['creativity', 'design', 'cloud', 'ai', 'javascript', 'typescript', 'ux'],
                'priority_skills': ['javascript', 'typescript', 'react', 'node.js', 'python', 'aws', 'docker'],
                'projects': ['Creative Tool', 'Design Application', 'Cloud Service', 'AI Feature'],
                'certifications': ['JavaScript Certification', 'React Certification', 'Cloud Computing'],
                'action_verbs': ['designed', 'created', 'built', 'innovated', 'launched'],
                'resume_tips': ['Show creativity', 'Highlight design thinking', 'Include user focus'],
                'min_ats_score': 80
            }
        }
        
        self.action_verbs = {
            'achievement': ['achieved', 'accomplished', 'attained', 'completed', 'delivered'],
            'leadership': ['led', 'managed', 'directed', 'coordinated', 'organized', 'supervised'],
            'improvement': ['improved', 'enhanced', 'optimized', 'upgraded', 'refined', 'strengthened'],
            'creation': ['created', 'developed', 'built', 'designed', 'implemented', 'launched'],
            'analysis': ['analyzed', 'evaluated', 'assessed', 'examined', 'investigated', 'studied'],
            'communication': ['presented', 'demonstrated', 'explained', 'proposed', 'recommended', 'negotiated']
        }
    
    def analyze_resume(self, resume_text, company_name):
        """Analyze resume against company requirements"""
        company = self.company_requirements.get(company_name, self.company_requirements['TCS'])
        text_lower = resume_text.lower()
        
        # Keyword analysis
        found_keywords = []
        missing_keywords = []
        for keyword in company['keywords']:
            if keyword in text_lower:
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        keyword_score = (len(found_keywords) / len(company['keywords'])) * 100
        
        # Skill analysis
        found_skills = []
        missing_skills = []
        for skill in company['priority_skills']:
            if skill in text_lower:
                found_skills.append(skill)
            else:
                missing_skills.append(skill)
        
        skill_score = (len(found_skills) / len(company['priority_skills'])) * 100
        
        # Action verb analysis
        verb_score = self._analyze_action_verbs(resume_text)
        
        # Calculate ATS score
        ats_score = (keyword_score * 0.4) + (skill_score * 0.4) + (verb_score * 0.2)
        ats_score = min(100, ats_score)
        
        # Calculate readiness score
        readiness_score = (ats_score / company['min_ats_score']) * 100 if company['min_ats_score'] > 0 else 0
        readiness_score = min(100, readiness_score)
        
        return {
            'ats_score': round(ats_score, 1),
            'readiness_score': round(readiness_score, 1),
            'keyword_score': round(keyword_score, 1),
            'skill_score': round(skill_score, 1),
            'verb_score': round(verb_score, 1),
            'found_keywords': found_keywords,
            'missing_keywords': missing_keywords[:10],
            'found_skills': found_skills,
            'missing_skills': missing_skills[:8],
            'meets_threshold': ats_score >= company['min_ats_score']
        }
    
    def _analyze_action_verbs(self, text):
        """Analyze action verb usage in resume"""
        text_lower = text.lower()
        total_verbs_found = 0
        total_verbs = sum(len(verbs) for verbs in self.action_verbs.values())
        
        for category, verbs in self.action_verbs.items():
            for verb in verbs:
                if verb in text_lower:
                    total_verbs_found += 1
        
        return (total_verbs_found / total_verbs) * 100 if total_verbs > 0 else 0
    
    def optimize_summary(self, original_summary, company_name):
        """Optimize professional summary for target company"""
        company = self.company_requirements.get(company_name, self.company_requirements['TCS'])
        
        # Extract key information from original summary
        words = original_summary.split()[:30]
        base_text = ' '.join(words)
        
        # Company-specific summary templates
        templates = {
            'TCS': f"Results-driven professional with expertise in Java, SQL, and web development. {base_text} Proven ability to work in teams and deliver quality solutions. Passionate about learning new technologies and solving complex problems.",
            'Infosys': f"Innovative software developer with strong foundation in Python and system design. {base_text} Experienced in building scalable applications and working in agile environments. Committed to continuous learning and technical excellence.",
            'Google': f"Passionate software engineer with deep understanding of data structures and algorithms. {base_text} Built scalable systems and optimized performance. Strong problem-solving skills with focus on technical excellence.",
            'Amazon': f"Customer-obsessed developer with experience in building scalable cloud solutions. {base_text} Proven track record of ownership and delivering results. Strong focus on operational excellence and frugality.",
            'Microsoft': f"Growth-minded engineer with expertise in cloud computing and AI technologies. {base_text} Passionate about innovation and building solutions that empower others. Strong foundation in .NET and Azure.",
            'default': f"Dedicated professional with strong technical skills and problem-solving abilities. {base_text} Committed to delivering high-quality work and continuous improvement."
        }
        
        template_key = company_name if company_name in templates else 'default'
        return templates[template_key][:300]
    
    def optimize_skills_section(self, skills_list, company_name):
        """Optimize skills section for target company"""
        company = self.company_requirements.get(company_name, self.company_requirements['TCS'])
        
        # Prioritize and reorder skills
        prioritized_skills = []
        for priority_skill in company['priority_skills']:
            for skill in skills_list:
                if priority_skill.lower() in skill.lower() or skill.lower() in priority_skill.lower():
                    if skill not in prioritized_skills:
                        prioritized_skills.append(skill)
        
        # Add remaining skills
        for skill in skills_list:
            if skill not in prioritized_skills:
                prioritized_skills.append(skill)
        
        # Add missing priority skills as recommendations
        recommended_skills = []
        for skill in company['priority_skills']:
            found = False
            for s in skills_list:
                if skill.lower() in s.lower() or s.lower() in skill.lower():
                    found = True
                    break
            if not found and skill not in recommended_skills:
                recommended_skills.append(skill)
        
        return {
            'optimized_skills': prioritized_skills[:15],
            'recommended_skills': recommended_skills[:5]
        }
    
    def optimize_project_description(self, project_title, project_desc, company_name):
        """Optimize project description for target company"""
        company = self.company_requirements.get(company_name, self.company_requirements['TCS'])
        
        # Add company-specific keywords to project description
        keywords_to_add = [k for k in company['keywords'][:3] if k not in project_desc.lower()]
        
        # Select appropriate action verb
        import random
        action_verb = random.choice(company['action_verbs'])
        
        optimized = f"{action_verb.capitalize()} {project_title}: {project_desc}"
        if keywords_to_add:
            optimized += f" Utilized {', '.join(keywords_to_add[:2])} for implementation."
        
        return optimized[:300]
    
    def optimize_achievement(self, achievement_text):
        """Convert simple statements into impactful achievements"""
        text_lower = achievement_text.lower()
        
        # Add metrics if missing
        if '%' not in achievement_text and 'percent' not in text_lower:
            import random
            metrics = ['15%', '25%', '30%', '40%', '50%']
            metric = random.choice(metrics)
            achievement_text += f" achieving {metric} improvement."
        
        # Add action verb if missing
        has_action_verb = any(verb in text_lower for verbs in self.action_verbs.values() for verb in verbs)
        if not has_action_verb:
            import random
            action_verbs = ['Successfully implemented', 'Led the development of', 'Architected and deployed', 'Delivered']
            achievement_text = f"{random.choice(action_verbs)} {achievement_text}"
        
        return achievement_text
    
    def generate_optimized_resume(self, resume_data, company_name, analysis_result):
        """Generate complete optimized resume for company"""
        company = self.company_requirements.get(company_name, self.company_requirements['TCS'])
        
        # Optimize each section
        optimized_summary = self.optimize_summary(resume_data.get('summary', ''), company_name)
        skills_optimization = self.optimize_skills_section(resume_data.get('skills', []), company_name)
        
        optimized_projects = []
        for project in resume_data.get('projects', []):
            opt = self.optimize_project_description(
                project.get('title', 'Project'),
                project.get('description', ''),
                company_name
            )
            optimized_projects.append({'title': project.get('title', ''), 'description': opt})
        
        optimized_achievements = []
        for achievement in resume_data.get('achievements', []):
            optimized_achievements.append(self.optimize_achievement(achievement))
        
        return {
            'summary': optimized_summary,
            'skills': skills_optimization['optimized_skills'],
            'recommended_skills': skills_optimization['recommended_skills'],
            'projects': optimized_projects,
            'achievements': optimized_achievements,
            'recommended_projects': company['projects'][:3],
            'recommended_certifications': company['certifications'][:3],
            'resume_tips': company['resume_tips'],
            'action_verbs_to_use': company['action_verbs'][:5]
        }
    
    def compare_companies(self, resume_data, companies):
        """Compare resume compatibility across multiple companies"""
        comparisons = []
        for company in companies:
            if company in self.company_requirements:
                analysis = self.analyze_resume(
                    json.dumps(resume_data.get('skills', [])) + ' ' + resume_data.get('summary', ''),
                    company
                )
                comparisons.append({
                    'company': company,
                    'ats_score': analysis['ats_score'],
                    'readiness_score': analysis['readiness_score'],
                    'meets_threshold': analysis['meets_threshold']
                })
        
        # Sort by ATS score
        comparisons.sort(key=lambda x: x['ats_score'], reverse=True)
        return comparisons
    
    def get_improvement_suggestions(self, analysis_result, company_name):
        """Get personalized improvement suggestions"""
        company = self.company_requirements.get(company_name, self.company_requirements['TCS'])
        suggestions = []
        
        if analysis_result['missing_keywords']:
            suggestions.append(f"Add these keywords to your resume: {', '.join(analysis_result['missing_keywords'][:5])}")
        
        if analysis_result['missing_skills']:
            suggestions.append(f"Learn and add these skills: {', '.join(analysis_result['missing_skills'][:4])}")
        
        if analysis_result['verb_score'] < 50:
            verbs = ', '.join(company['action_verbs'][:4])
            suggestions.append(f"Use strong action verbs like: {verbs}")
        
        suggestions.extend(company['resume_tips'])
        suggestions.append(f"Aim for ATS score above {company['min_ats_score']}%")
        suggestions.append("Quantify achievements with numbers and percentages")
        suggestions.append("Use standard section headings (Experience, Education, Skills)")
        
        return suggestions[:8]