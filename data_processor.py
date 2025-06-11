import csv
import json
import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any
from config import Config

class DataProcessor:
    """数据处理类，负责数据转换和存储"""
    
    def __init__(self):
        Config.ensure_output_dir()
        
    def save_to_excel(self, data: Dict, api_name: str, keyword: str = "") -> str:
        """
        将API响应数据保存为Excel文件，按日期分类存储
        
        Args:
            data: API响应数据
            api_name: API名称
            keyword: 搜索关键词
            
        Returns:
            保存的文件路径
        """
        # 创建日期目录
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = os.path.join(Config.OUTPUT_DIR, date_str)
        if not os.path.exists(date_dir):
            os.makedirs(date_dir)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%H%M%S")
        keyword_suffix = f"_{keyword}" if keyword else ""
        filename = f"{api_name}{keyword_suffix}_{timestamp}.xlsx"
        filepath = os.path.join(date_dir, filename)
        
        # 提取并扁平化数据
        flattened_data = self._flatten_json(data)
        
        if not flattened_data:
            # 如果没有数据，至少保存原始响应结构
            flattened_data = [{'raw_response': json.dumps(data, ensure_ascii=False)}]
        
        # 转换为DataFrame并保存为Excel
        try:
            df = pd.DataFrame(flattened_data)
            
            # 使用ExcelWriter来更好地控制格式
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # 主数据表
                df.to_excel(writer, sheet_name='搜索数据', index=False)
                
                # 元数据表
                metadata = {
                    '爬取时间': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                    '关键词': [keyword],
                    'API名称': [api_name],
                    '数据条数': [len(flattened_data)],
                    '提取方法': [data.get('extraction_method', 'api_request')]
                }
                
                if 'page_url' in data:
                    metadata['页面URL'] = [data['page_url']]
                if 'total_count' in data:
                    metadata['总数量'] = [data['total_count']]
                
                metadata_df = pd.DataFrame(metadata)
                metadata_df.to_excel(writer, sheet_name='元数据', index=False)
                
                # 如果有原始JSON数据，保存到第三个表
                if 'raw_json_data' in data:
                    raw_json_df = pd.DataFrame({
                        '原始JSON': data['raw_json_data']
                    })
                    raw_json_df.to_excel(writer, sheet_name='原始数据', index=False)
                
                # 自动调整列宽
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)  # 限制最大宽度
                        worksheet.column_dimensions[column_letter].width = adjusted_width
            
            return filepath
            
        except Exception as e:
            # 如果Excel保存失败，回退到CSV
            print(f"Excel保存失败，回退到CSV: {str(e)}")
            return self.save_to_csv(data, api_name, keyword)
    
    def save_to_csv(self, data: Dict, api_name: str, keyword: str = "") -> str:
        """
        将API响应数据保存为CSV文件（备用方案）
        
        Args:
            data: API响应数据
            api_name: API名称
            keyword: 搜索关键词
            
        Returns:
            保存的文件路径
        """
        # 创建日期目录
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = os.path.join(Config.OUTPUT_DIR, date_str)
        if not os.path.exists(date_dir):
            os.makedirs(date_dir)
        
        timestamp = datetime.now().strftime("%H%M%S")
        keyword_suffix = f"_{keyword}" if keyword else ""
        filename = f"{api_name}{keyword_suffix}_{timestamp}.csv"
        filepath = os.path.join(date_dir, filename)
        
        # 提取并扁平化数据
        flattened_data = self._flatten_json(data)
        
        if not flattened_data:
            flattened_data = [{'raw_response': json.dumps(data, ensure_ascii=False)}]
        
        # 写入CSV文件
        fieldnames = list(flattened_data[0].keys())
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattened_data)
        
        return filepath
    
    def _flatten_json(self, data: Any, prefix: str = '') -> List[Dict]:
        """
        递归扁平化JSON数据
        
        Args:
            data: 要扁平化的数据
            prefix: 字段前缀
            
        Returns:
            扁平化后的数据列表
        """
        if isinstance(data, dict):
            result = []
            # 如果字典包含列表类型的值，可能需要特殊处理
            if any(isinstance(v, list) and v for v in data.values()):
                # 找到最长的列表作为主要数据源
                list_fields = {k: v for k, v in data.items() if isinstance(v, list) and v}
                if list_fields:
                    max_length = max(len(v) for v in list_fields.values())
                    for i in range(max_length):
                        row = {}
                        for key, value in data.items():
                            if isinstance(value, list) and value:
                                if i < len(value):
                                    if isinstance(value[i], dict):
                                        # 递归处理嵌套字典
                                        nested = self._flatten_dict(value[i], f"{prefix}{key}_")
                                        row.update(nested)
                                    else:
                                        row[f"{prefix}{key}"] = value[i]
                                else:
                                    row[f"{prefix}{key}"] = ""
                            elif not isinstance(value, list):
                                if isinstance(value, dict):
                                    nested = self._flatten_dict(value, f"{prefix}{key}_")
                                    row.update(nested)
                                else:
                                    row[f"{prefix}{key}"] = value
                        result.append(row)
                    return result
            
            # 普通字典处理
            return [self._flatten_dict(data, prefix)]
        
        elif isinstance(data, list) and data:
            result = []
            for item in data:
                result.extend(self._flatten_json(item, prefix))
            return result
        
        else:
            return [{f"{prefix}value": data}]
    
    def _flatten_dict(self, data: Dict, prefix: str = '') -> Dict:
        """扁平化单个字典"""
        result = {}
        for key, value in data.items():
            new_key = f"{prefix}{key}"
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, f"{new_key}_"))
            elif isinstance(value, list):
                # 简单处理列表，转为字符串
                result[new_key] = json.dumps(value, ensure_ascii=False) if value else ""
            else:
                result[new_key] = value
        return result
