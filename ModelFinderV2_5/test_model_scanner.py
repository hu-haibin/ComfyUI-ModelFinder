"""
模型扫描器测试脚本
用于验证模型扫描功能的性能和稳定性
"""
import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from model_scanner import ModelScanner
from logger_config import setup_logger
import logging

logger = setup_logger(logging.DEBUG)


def create_test_files(test_dir: str, num_files: int = 20):
    """创建测试文件"""
    logger.info(f"创建测试目录: {test_dir}")
    
    # 创建不同类型的模型目录
    subdirs = [
        'checkpoints',
        'loras',
        'controlnet',
        'vae',
        'upscale_models'
    ]
    
    for subdir in subdirs:
        dir_path = os.path.join(test_dir, subdir)
        os.makedirs(dir_path, exist_ok=True)
    
    # 创建测试文件
    for i in range(num_files):
        subdir = subdirs[i % len(subdirs)]
        file_name = f"test_model_{i}.safetensors"
        file_path = os.path.join(test_dir, subdir, file_name)
        
        # 创建不同大小的文件（模拟真实模型）
        file_size = 1024 * 1024 * (i % 10 + 1)  # 1-10 MB
        
        with open(file_path, 'wb') as f:
            # 写入随机数据
            f.write(os.urandom(file_size))
        
        logger.debug(f"创建测试文件: {file_path} ({file_size / 1024 / 1024:.2f} MB)")
    
    logger.info(f"创建了 {num_files} 个测试文件")


def test_basic_scan():
    """测试基本扫描功能"""
    logger.info("=" * 60)
    logger.info("测试 1: 基本扫描功能")
    logger.info("=" * 60)
    
    # 创建临时测试目录
    test_dir = tempfile.mkdtemp(prefix='model_scanner_test_')
    cache_file = os.path.join(test_dir, 'test_cache.json')
    
    try:
        # 创建测试文件
        create_test_files(test_dir, num_files=10)
        
        # 初始化扫描器
        scanner = ModelScanner(cache_file=cache_file)
        
        # 开始扫描
        logger.info("开始扫描...")
        start_time = time.time()
        
        scanner.scan_directory(test_dir)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # 检查结果
        models = scanner.models
        logger.info(f"扫描完成！耗时: {elapsed:.2f} 秒")
        logger.info(f"找到模型数量: {len(models)}")
        
        # 验证结果
        assert len(models) == 10, f"期望 10 个模型，实际找到 {len(models)} 个"
        
        # 验证哈希值
        for model in models:
            assert model['hash'] is not None, f"模型 {model['name']} 没有哈希值"
            assert len(model['hash']) == 64, f"哈希值长度不正确: {len(model['hash'])}"
        
        # 验证类型识别
        type_counts = {}
        for model in models:
            model_type = model['type']
            type_counts[model_type] = type_counts.get(model_type, 0) + 1
        
        logger.info(f"类型分布: {type_counts}")
        
        logger.info("✅ 基本扫描功能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False
    finally:
        # 清理
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            logger.info(f"清理测试目录: {test_dir}")


def test_cache_performance():
    """测试缓存性能"""
    logger.info("=" * 60)
    logger.info("测试 2: 缓存性能")
    logger.info("=" * 60)
    
    test_dir = tempfile.mkdtemp(prefix='model_scanner_cache_')
    cache_file = os.path.join(test_dir, 'test_cache.json')
    
    try:
        # 创建测试文件
        create_test_files(test_dir, num_files=15)
        
        # 第一次扫描（无缓存）
        scanner1 = ModelScanner(cache_file=cache_file)
        logger.info("第一次扫描（无缓存）...")
        start_time = time.time()
        scanner1.scan_directory(test_dir)
        first_scan_time = time.time() - start_time
        logger.info(f"第一次扫描耗时: {first_scan_time:.2f} 秒")
        
        # 第二次扫描（使用缓存）
        scanner2 = ModelScanner(cache_file=cache_file)
        logger.info("第二次扫描（使用缓存）...")
        start_time = time.time()
        scanner2.scan_directory(test_dir)
        second_scan_time = time.time() - start_time
        logger.info(f"第二次扫描耗时: {second_scan_time:.2f} 秒")
        
        # 验证缓存效果
        speedup = first_scan_time / second_scan_time if second_scan_time > 0 else 0
        logger.info(f"缓存加速比: {speedup:.2f}x")
        
        assert second_scan_time < first_scan_time, "缓存应该提升速度"
        
        logger.info("✅ 缓存性能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_cancel_scan():
    """测试取消扫描"""
    logger.info("=" * 60)
    logger.info("测试 3: 取消扫描")
    logger.info("=" * 60)
    
    test_dir = tempfile.mkdtemp(prefix='model_scanner_cancel_')
    cache_file = os.path.join(test_dir, 'test_cache.json')
    
    try:
        # 创建较多测试文件
        create_test_files(test_dir, num_files=30)
        
        scanner = ModelScanner(cache_file=cache_file)
        
        # 启动后台扫描
        logger.info("启动后台扫描...")
        scanner.start_scan(test_dir)
        
        # 等待一小段时间
        time.sleep(1)
        
        # 取消扫描
        logger.info("请求取消扫描...")
        scanner.stop_scan()
        
        # 验证状态
        progress = scanner.get_progress()
        logger.info(f"最终状态: {progress['status']}")
        logger.info(f"已扫描: {progress['scanned_files']}/{progress['total_files']}")
        
        assert progress['status'] in ['cancelled', 'completed'], f"状态不正确: {progress['status']}"
        
        logger.info("✅ 取消扫描测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def test_query_functions():
    """测试查询功能"""
    logger.info("=" * 60)
    logger.info("测试 4: 查询功能")
    logger.info("=" * 60)
    
    test_dir = tempfile.mkdtemp(prefix='model_scanner_query_')
    cache_file = os.path.join(test_dir, 'test_cache.json')
    
    try:
        # 创建测试文件
        create_test_files(test_dir, num_files=20)
        
        scanner = ModelScanner(cache_file=cache_file)
        scanner.scan_directory(test_dir)
        
        # 测试搜索
        logger.info("测试搜索功能...")
        result = scanner.get_models(search_term='test_model_5')
        assert len(result['models']) == 1, "搜索结果数量不正确"
        logger.info(f"搜索 'test_model_5': 找到 {len(result['models'])} 个")
        
        # 测试类型筛选
        logger.info("测试类型筛选...")
        result = scanner.get_models(model_type='Checkpoint')
        logger.info(f"筛选 'Checkpoint': 找到 {len(result['models'])} 个")
        
        # 测试排序
        logger.info("测试排序...")
        result_asc = scanner.get_models(sort_by='size', sort_order='asc')
        result_desc = scanner.get_models(sort_by='size', sort_order='desc')
        if len(result_asc['models']) > 0 and len(result_desc['models']) > 0:
            assert result_asc['models'][0]['size'] <= result_desc['models'][0]['size'], "排序不正确"
        
        # 测试分页
        logger.info("测试分页...")
        result_page1 = scanner.get_models(limit=5, offset=0)
        result_page2 = scanner.get_models(limit=5, offset=5)
        assert len(result_page1['models']) == 5, "第一页数量不正确"
        assert len(result_page2['models']) == 5, "第二页数量不正确"
        
        # 测试统计
        logger.info("测试统计功能...")
        stats = scanner.get_statistics()
        logger.info(f"统计: {stats['total_models']} 个模型，总大小 {stats['total_size_formatted']}")
        assert stats['total_models'] == 20, "统计数量不正确"
        
        logger.info("✅ 查询功能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False
    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def run_all_tests():
    """运行所有测试"""
    logger.info("开始运行模型扫描器测试套件...")
    logger.info("")
    
    tests = [
        ("基本扫描功能", test_basic_scan),
        ("缓存性能", test_cache_performance),
        ("取消扫描", test_cancel_scan),
        ("查询功能", test_query_functions),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"测试 '{test_name}' 出现异常: {e}", exc_info=True)
            failed += 1
        logger.info("")
    
    # 输出总结
    logger.info("=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    logger.info(f"通过: {passed}/{len(tests)}")
    logger.info(f"失败: {failed}/{len(tests)}")
    
    if failed == 0:
        logger.info("✅ 所有测试通过！")
    else:
        logger.warning(f"⚠️ {failed} 个测试失败")
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

