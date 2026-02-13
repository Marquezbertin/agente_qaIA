"""
Knowledge Base - Sistema RAG para Base de Conhecimento
======================================================

Indexa documentos e permite busca semantica para
fornecer contexto relevante ao agente.
"""

import os
import re
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import math


@dataclass
class Document:
    """Representa um documento na base de conhecimento"""
    id: str
    content: str
    source: str
    doc_type: str
    chunks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    indexed_at: datetime = field(default_factory=datetime.now)


class KnowledgeBase:
    """
    Base de conhecimento com busca por similaridade.

    Implementa um sistema RAG simplificado usando TF-IDF
    para busca sem dependencias externas pesadas.
    """

    # Extensoes suportadas
    SUPPORTED_EXTENSIONS = {
        ".py": "python",
        ".cs": "csharp",
        ".js": "javascript",
        ".ts": "typescript",
        ".md": "markdown",
        ".txt": "text",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".feature": "gherkin",
        ".sql": "sql",
        ".ini": "config",
        ".env": "config"
    }

    # Padroes para ignorar
    IGNORE_PATTERNS = [
        r"\.venv", r"node_modules", r"__pycache__", r"\.git",
        r"\.pytest_cache", r"dist", r"build", r"\.egg-info",
        r"\.tox", r"\.coverage", r"\.mypy_cache"
    ]

    # Tamanho do chunk
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200

    def __init__(self, persist_path: Optional[Path] = None):
        self.documents: Dict[str, Document] = {}
        self.index: Dict[str, Dict[str, float]] = {}  # term -> {doc_id: tf-idf}
        self.doc_vectors: Dict[str, Dict[str, float]] = {}  # doc_id -> {term: tf-idf}
        self.persist_path = persist_path or Path(__file__).parent.parent / "knowledge_base"
        self.persist_path.mkdir(exist_ok=True)

        # Carregar indice persistido
        self._load_index()

    def add_document(
        self,
        content: str,
        source: str,
        doc_type: str = "text",
        metadata: Optional[Dict] = None
    ) -> str:
        """Adiciona documento a base de conhecimento"""
        # Gerar ID unico
        doc_id = hashlib.md5(f"{source}:{content[:100]}".encode()).hexdigest()[:12]

        # Verificar se ja existe
        if doc_id in self.documents:
            return doc_id

        # Criar chunks
        chunks = self._create_chunks(content)

        # Criar documento
        doc = Document(
            id=doc_id,
            content=content,
            source=source,
            doc_type=doc_type,
            chunks=chunks,
            metadata=metadata or {}
        )

        self.documents[doc_id] = doc

        # Indexar
        self._index_document(doc)

        return doc_id

    def _create_chunks(self, content: str) -> List[str]:
        """Divide conteudo em chunks com overlap"""
        chunks = []
        start = 0

        while start < len(content):
            end = start + self.CHUNK_SIZE

            # Tentar cortar em quebra de linha
            if end < len(content):
                newline_pos = content.rfind('\n', start, end)
                if newline_pos > start + self.CHUNK_SIZE // 2:
                    end = newline_pos + 1

            chunk = content[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.CHUNK_OVERLAP

        return chunks

    def _index_document(self, doc: Document):
        """Indexa documento usando TF-IDF simplificado"""
        # Tokenizar todo o conteudo
        tokens = self._tokenize(doc.content)

        # Calcular frequencia de termos
        term_freq = {}
        for token in tokens:
            term_freq[token] = term_freq.get(token, 0) + 1

        # Normalizar por tamanho do documento
        doc_length = len(tokens)
        if doc_length == 0:
            return

        doc_vector = {}
        for term, freq in term_freq.items():
            tf = freq / doc_length
            doc_vector[term] = tf

            # Adicionar ao indice invertido
            if term not in self.index:
                self.index[term] = {}
            self.index[term][doc.id] = tf

        self.doc_vectors[doc.id] = doc_vector

    def _tokenize(self, text: str) -> List[str]:
        """Tokeniza texto em palavras"""
        # Converter para minusculas
        text = text.lower()

        # Remover caracteres especiais, manter letras e numeros
        text = re.sub(r'[^a-z0-9\s_]', ' ', text)

        # Dividir em palavras
        tokens = text.split()

        # Filtrar stopwords e palavras muito curtas
        stopwords = {
            'a', 'o', 'e', 'de', 'da', 'do', 'em', 'para', 'com', 'por',
            'que', 'um', 'uma', 'os', 'as', 'na', 'no', 'se', 'ou', 'ao',
            'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can',
            'def', 'class', 'import', 'from', 'return', 'if', 'else',
            'self', 'none', 'true', 'false', 'and', 'or', 'not', 'in'
        }

        tokens = [t for t in tokens if len(t) > 2 and t not in stopwords]

        return tokens

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Busca documentos relevantes para a query"""
        if not self.documents:
            return []

        # Tokenizar query
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return []

        # Calcular scores para cada documento
        scores = {}

        for token in query_tokens:
            if token in self.index:
                # IDF aproximado
                idf = math.log(len(self.documents) / (len(self.index[token]) + 1)) + 1

                for doc_id, tf in self.index[token].items():
                    if doc_id not in scores:
                        scores[doc_id] = 0
                    scores[doc_id] += tf * idf

        # Ordenar por score
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Retornar top_k
        results = []
        for doc_id, score in sorted_docs[:top_k]:
            doc = self.documents[doc_id]

            # Encontrar chunk mais relevante
            best_chunk = self._find_best_chunk(doc, query_tokens)

            results.append({
                "id": doc_id,
                "source": doc.source,
                "doc_type": doc.doc_type,
                "content": best_chunk,
                "score": score,
                "metadata": doc.metadata
            })

        return results

    def _find_best_chunk(self, doc: Document, query_tokens: List[str]) -> str:
        """Encontra o chunk mais relevante do documento"""
        if not doc.chunks:
            return doc.content[:self.CHUNK_SIZE]

        best_chunk = doc.chunks[0]
        best_score = 0

        for chunk in doc.chunks:
            chunk_lower = chunk.lower()
            score = sum(1 for token in query_tokens if token in chunk_lower)

            if score > best_score:
                best_score = score
                best_chunk = chunk

        return best_chunk

    def index_directory(self, directory: Path, recursive: bool = True):
        """Indexa todos os arquivos de um diretorio"""
        if not directory.exists():
            return 0

        count = 0
        pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(pattern):
            if not file_path.is_file():
                continue

            # Verificar se deve ignorar
            if self._should_ignore(str(file_path)):
                continue

            # Verificar extensao
            ext = file_path.suffix.lower()
            if ext not in self.SUPPORTED_EXTENSIONS:
                continue

            try:
                content = self._read_file(file_path)
                if content:
                    self.add_document(
                        content=content,
                        source=str(file_path.relative_to(directory)),
                        doc_type=self.SUPPORTED_EXTENSIONS[ext],
                        metadata={"full_path": str(file_path)}
                    )
                    count += 1
            except Exception:
                continue

        return count

    def _should_ignore(self, path: str) -> bool:
        """Verifica se o caminho deve ser ignorado"""
        for pattern in self.IGNORE_PATTERNS:
            if re.search(pattern, path):
                return True
        return False

    def _read_file(self, path: Path, max_size: int = 100000) -> Optional[str]:
        """Le conteudo de um arquivo"""
        try:
            if path.stat().st_size > max_size:
                return None

            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return None

    def _save_index(self):
        """Persiste o indice em disco"""
        index_file = self.persist_path / "index.json"

        data = {
            "documents": {
                doc_id: {
                    "source": doc.source,
                    "doc_type": doc.doc_type,
                    "content_hash": hashlib.md5(doc.content.encode()).hexdigest(),
                    "metadata": doc.metadata
                }
                for doc_id, doc in self.documents.items()
            },
            "indexed_at": datetime.now().isoformat()
        }

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load_index(self):
        """Carrega indice do disco"""
        index_file = self.persist_path / "index.json"

        if not index_file.exists():
            return

        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Index seria reconstruido na proxima indexacao
        except Exception:
            pass

    def get_stats(self) -> Dict:
        """Retorna estatisticas da base de conhecimento"""
        return {
            "total_documents": len(self.documents),
            "total_terms": len(self.index),
            "by_type": self._count_by_type(),
            "sources": list(set(doc.source for doc in self.documents.values()))[:20]
        }

    def _count_by_type(self) -> Dict[str, int]:
        """Conta documentos por tipo"""
        counts = {}
        for doc in self.documents.values():
            counts[doc.doc_type] = counts.get(doc.doc_type, 0) + 1
        return counts

    def clear(self):
        """Limpa toda a base de conhecimento"""
        self.documents.clear()
        self.index.clear()
        self.doc_vectors.clear()

    def remove_document(self, doc_id: str):
        """Remove um documento da base"""
        if doc_id not in self.documents:
            return

        # Remover do indice
        doc = self.documents[doc_id]
        tokens = self._tokenize(doc.content)

        for token in set(tokens):
            if token in self.index and doc_id in self.index[token]:
                del self.index[token][doc_id]
                if not self.index[token]:
                    del self.index[token]

        # Remover documento
        del self.documents[doc_id]
        if doc_id in self.doc_vectors:
            del self.doc_vectors[doc_id]
