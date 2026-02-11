import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class MatchingAlgorithm:
    def __init__(self):
        # Веса для различных критериев
        self.weights = {
            'city': 0.25,
            'object_type': 0.20,
            'work_type': 0.20,
            'budget': 0.15,
            'square': 0.10,
            'description': 0.10
        }
    
    def calculate_match_score(self, request1, request2):
        """Рассчитывает процент совпадения между двумя заявками"""
        score = 0
        
        # Город (полное совпадение)
        if request1[3] == request2[3]:  # city
            score += self.weights['city']
        
        # Тип объекта (полное совпадение)
        if request1[4] == request2[4]:  # object_type
            score += self.weights['object_type']
        
        # Вид работ (частичное совпадение)
        if request1[5] == request2[5]:  # work_type
            score += self.weights['work_type']
        elif self._work_types_compatible(request1[5], request2[5]):
            score += self.weights['work_type'] * 0.5
        
        # Бюджет
        if self._budget_match(request1[6], request2[6]):  # budget_range
            score += self.weights['budget']
        
        # Площадь (чем ближе, тем выше балл)
        square_score = self._calculate_square_similarity(request1[7], request2[7])
        score += self.weights['square'] * square_score
        
        # Описание (текстовое сходство)
        desc_similarity = self._calculate_text_similarity(
            request1[8] or "", 
            request2[8] or ""
        )
        score += self.weights['description'] * desc_similarity
        
        return round(score * 100, 2)  # Возвращаем проценты
    
    def _work_types_compatible(self, wt1, wt2):
        """Проверяет совместимость видов работ"""
        compatible_pairs = [
            ('full', 'capital'),
            ('full', 'cosmetic'),
            ('capital', 'rough'),
            ('finishing', 'cosmetic'),
            ('electrics', 'plumbing')
        ]
        return (wt1, wt2) in compatible_pairs or (wt2, wt1) in compatible_pairs
    
    def _budget_match(self, budget1, budget2):
        """Проверяет совместимость бюджетов"""
        if budget1 == budget2:
            return True
        
        budget_levels = ['low', 'medium', 'high', 'premium']
        if budget1 in budget_levels and budget2 in budget_levels:
            idx1 = budget_levels.index(budget1)
            idx2 = budget_levels.index(budget2)
            return abs(idx1 - idx2) <= 1  # Соседние категории
        
        return False
    
    def _calculate_square_similarity(self, sq1, sq2):
        """Рассчитывает схожесть по площади"""
        if not sq1 or not sq2:
            return 0.5
        
        diff_percent = abs(sq1 - sq2) / max(sq1, sq2)
        return max(0, 1 - diff_percent)
    
    def _calculate_text_similarity(self, text1, text2):
        """Рассчитывает текстовое сходство описаний"""
        if not text1 or not text2:
            return 0.5
        
        vectorizer = TfidfVectorizer().fit_transform([text1, text2])
        vectors = vectorizer.toarray()
        return cosine_similarity([vectors[0]], [vectors[1]])[0][0]
    
    def find_best_matches(self, target_request, all_requests, limit=10):
        """Находит лучшие совпадения для конкретной заявки"""
        matches = []
        
        for request in all_requests:
            # Не сравниваем заявку с самой собой
            if request[0] == target_request[0]:
                continue
            
            # Прорабы ищут собственников, собственники ищут прорабов
            if request[2] == target_request[2]:  # user_type
                continue
            
            score = self.calculate_match_score(target_request, request)
            if score > 30:  # Минимальный порог совпадения 30%
                matches.append((request, score))
        
        # Сортируем по убыванию совпадения
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:limit]