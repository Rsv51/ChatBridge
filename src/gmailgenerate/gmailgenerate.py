import random
import string
import itertools

class GmailAliasGenerator:
    def __init__(self, base_email):
        """
        初始化Gmail别名生成器
        
        Args:
            base_email (str): 基础邮箱地址，如 aaa@gmail.com
        """
        if '@' not in base_email:
            raise ValueError("请输入有效的邮箱地址")
        
        self.username, self.domain = base_email.split('@', 1)
        self.base_email = base_email
        
        # 支持的域名后缀
        self.domain_suffixes = [
            'gmail.com',
            'googlemail.com',
            'google.cn',
            'google.com.hk',
            'google.com.jp',
            'google.co.uk',
            'google.de',
            'google.fr'
        ]
        
        # 常用的+号后缀
        self.common_plus_suffixes = [
            'aws', 'ali', 'huawei', 'tencent', 'baidu', 'microsoft',
            'apple', 'facebook', 'twitter', 'instagram', 'linkedin',
            'github', 'gitlab', 'stackoverflow', 'reddit', 'youtube',
            'netflix', 'amazon', 'ebay', 'paypal', 'stripe', 'discord',
            'telegram', 'whatsapp', 'wechat', 'qq', 'weibo', 'douyin',
            'shopping', 'work', 'personal', 'business', 'test', 'dev',
            'prod', 'staging', 'demo', 'trial', 'backup', 'main',
            'primary', 'secondary', 'temp', 'temporary', 'spam',
            'newsletter', 'promotion', 'deal', 'coupon', 'subscribe'
        ]
    
    def generate_plus_alias(self, suffix=None):
        """
        生成使用+号的别名
        
        Args:
            suffix (str, optional): 自定义后缀，如果不提供则随机生成
            
        Returns:
            str: 别名邮箱
        """
        if suffix is None:
            # 随机选择常用后缀或生成随机字符串
            if random.choice([True, False]):
                suffix = random.choice(self.common_plus_suffixes)
            else:
                length = random.randint(3, 20)
                suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        
        domain = random.choice(self.domain_suffixes)
        return f"{self.username}+{suffix}@{domain}"
    
    def generate_dot_alias(self):
        """
        生成使用小数点的别名
        
        Returns:
            str: 别名邮箱
        """
        username = self.username
        # 随机在用户名中插入小数点
        if len(username) > 1:
            positions = list(range(1, len(username)))
            num_dots = random.randint(1, min(3, len(positions)))
            dot_positions = sorted(random.sample(positions, num_dots))
            
            result = []
            last_pos = 0
            for pos in dot_positions:
                result.append(username[last_pos:pos])
                result.append('.')
                last_pos = pos
            result.append(username[last_pos:])
            
            username = ''.join(result)
        
        domain = random.choice(self.domain_suffixes)
        return f"{username}@{domain}"
    
    def generate_case_alias(self):
        """
        生成改变大小写的别名
        
        Returns:
            str: 别名邮箱
        """
        username = self.username
        # 随机改变字符大小写
        result = []
        for char in username:
            if char.isalpha():
                result.append(char.upper() if random.choice([True, False]) else char.lower())
            else:
                result.append(char)
        
        domain = random.choice(self.domain_suffixes)
        return f"{''.join(result)}@{domain}"
    
    def generate_domain_alias(self):
        """
        生成使用不同域名后缀的别名
        
        Returns:
            str: 别名邮箱
        """
        domain = random.choice(self.domain_suffixes)
        return f"{self.username}@{domain}"
    
    def generate_combined_alias(self):
        """
        生成组合多种规则的别名
        
        Returns:
            str: 别名邮箱
        """
        username = self.username
        
        # 1. 随机改变大小写
        case_username = []
        for char in username:
            if char.isalpha():
                case_username.append(char.upper() if random.choice([True, False]) else char.lower())
            else:
                case_username.append(char)
        username = ''.join(case_username)
        
        # 2. 随机添加小数点
        if len(username) > 1 and random.choice([True, False]):
            positions = list(range(1, len(username)))
            num_dots = random.randint(1, min(2, len(positions)))
            dot_positions = sorted(random.sample(positions, num_dots))
            
            result = []
            last_pos = 0
            for pos in dot_positions:
                result.append(username[last_pos:pos])
                result.append('.')
                last_pos = pos
            result.append(username[last_pos:])
            username = ''.join(result)
        
        # 3. 随机添加+号后缀
        if random.choice([True, False]):
            if random.choice([True, False]):
                suffix = random.choice(self.common_plus_suffixes)
            else:
                length = random.randint(5, 30)
                suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
            username += f"+{suffix}"
        
        # 4. 选择随机域名
        domain = random.choice(self.domain_suffixes)
        
        return f"{username}@{domain}"
    
    def generate_aliases(self, count=10):
        """
        生成指定数量的别名
        
        Args:
            count (int): 要生成的别名数量
            
        Returns:
            list: 别名列表
        """
        aliases = []
        methods = [
            self.generate_plus_alias,
            self.generate_dot_alias,
            self.generate_case_alias,
            self.generate_domain_alias,
            self.generate_combined_alias
        ]
        
        for _ in range(count):
            method = random.choice(methods)
            alias = method()
            aliases.append(alias)
        
        return aliases
    
    def generate_specific_type_aliases(self, alias_type, count=10):
        """
        生成特定类型的别名
        
        Args:
            alias_type (str): 别名类型 ('plus', 'dot', 'case', 'domain', 'combined')
            count (int): 要生成的别名数量
            
        Returns:
            list: 别名列表
        """
        method_map = {
            'plus': self.generate_plus_alias,
            'dot': self.generate_dot_alias,
            'case': self.generate_case_alias,
            'domain': self.generate_domain_alias,
            'combined': self.generate_combined_alias
        }
        
        if alias_type not in method_map:
            raise ValueError(f"不支持的别名类型: {alias_type}")
        
        method = method_map[alias_type]
        aliases = []
        
        for _ in range(count):
            alias = method()
            aliases.append(alias)
        
        return aliases


def main():
    """
    主函数，演示如何使用Gmail别名生成器
    """
    # 示例用法
    base_email = "aaa@gmail.com"
    generator = GmailAliasGenerator(base_email)
    
    print(f"基础邮箱: {base_email}")
    print("=" * 50)
    
    # 生成不同类型的别名
    print("1. +号别名:")
    plus_aliases = generator.generate_specific_type_aliases('plus', 5)
    for alias in plus_aliases:
        print(f"   {alias}")
    
    print("\n2. 小数点别名:")
    dot_aliases = generator.generate_specific_type_aliases('dot', 5)
    for alias in dot_aliases:
        print(f"   {alias}")
    
    print("\n3. 大小写别名:")
    case_aliases = generator.generate_specific_type_aliases('case', 5)
    for alias in case_aliases:
        print(f"   {alias}")
    
    print("\n4. 域名别名:")
    domain_aliases = generator.generate_specific_type_aliases('domain', 5)
    for alias in domain_aliases:
        print(f"   {alias}")
    
    print("\n5. 组合别名:")
    combined_aliases = generator.generate_specific_type_aliases('combined', 5)
    for alias in combined_aliases:
        print(f"   {alias}")
    
    print("\n6. 混合随机别名:")
    mixed_aliases = generator.generate_aliases(10)
    for alias in mixed_aliases:
        print(f"   {alias}")


if __name__ == "__main__":
    main()