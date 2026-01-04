import sys
from pathlib import Path
from typing import Any, Dict, List
import logging

sys.path.insert(0, str(Path(__file__).parent))

from utils.data_structures import StaticMap
from utils.path_utils import normalize_path
from utils.toon_parser import parse_toon_file

logger = logging.getLogger(__name__)


class ReportContextLoader:
    
    def load_structure_map(self, path: Path) -> Dict[Path, List[Any]]:
        normalized_path = normalize_path(path)
        
        if not normalized_path.exists():
            logger.warning(f"Structure file not found: {normalized_path}")
            return {}
        
        try:
            data = parse_toon_file(normalized_path)
            structure_map: Dict[Path, List[Any]] = {}

            if 'structure' in data:
                for item in data['structure']:
                    if isinstance(item, dict) and 'file_path' in item:
                        file_path = normalize_path(item['file_path'])
                        if file_path not in structure_map:
                            structure_map[file_path] = []
                        structure_map[file_path].append(item)
            
            return structure_map
        except Exception as e:
            logger.error(f"Failed to parse structure file: {e}")
            return {}
    
    def load_quality_metrics(self, path: Path) -> Dict[Path, List[Any]]:
        normalized_path = normalize_path(path)
        
        if not normalized_path.exists():
            logger.warning(f"Quality report file not found: {normalized_path}")
            return {}
        
        try:
            data = parse_toon_file(normalized_path)
            quality_map: Dict[Path, List[Any]] = {}

            if 'issues' in data:
                for item in data['issues']:
                    if isinstance(item, dict) and 'file_path' in item:
                        file_path = normalize_path(item['file_path'])
                        if file_path not in quality_map:
                            quality_map[file_path] = []
                        quality_map[file_path].append(item)
            
            return quality_map
        except Exception as e:
            logger.error(f"Failed to parse quality report file: {e}")
            return {}
    
    def load_static_context(self, structure_path: Path, quality_path: Path) -> StaticMap:
        structure_map = self.load_structure_map(structure_path)
        quality_map = self.load_quality_metrics(quality_path)
        return StaticMap(structure_map=structure_map, quality_map=quality_map)
    
    def load_structure_data(self, path: Path) -> Dict[str, Any]:
        normalized_path = normalize_path(path)
        
        if not normalized_path.exists():
            logger.warning(f"Structure file not found: {normalized_path}")
            return {}
        
        try:
            data = parse_toon_file(normalized_path)
            return data
        except Exception as e:
            logger.error(f"Failed to parse structure file: {e}")
            return {}
    
    def load_quality_data(self, path: Path) -> Dict[str, Any]:
        normalized_path = normalize_path(path)
        
        if not normalized_path.exists():
            logger.warning(f"Quality report file not found: {normalized_path}")
            return {}
        
        try:
            data = parse_toon_file(normalized_path)
            return data
        except Exception as e:
            logger.error(f"Failed to parse quality report file: {e}")
            return {}
    
    def load_full_analysis_data(self, structure_path: Path, quality_path: Path) -> tuple[Dict[str, Any], Dict[str, Any]]:
        structure_data = self.load_structure_data(structure_path)
        quality_data = self.load_quality_data(quality_path)
        return structure_data, quality_data
