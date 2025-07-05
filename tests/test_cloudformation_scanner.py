"""Test cases for CloudFormation scanner."""
import pytest
import tempfile
import json
import yaml
from pathlib import Path
from dependency_scanner_tool.infrastructure_scanners.cloudformation import CloudFormationScanner
from dependency_scanner_tool.models.infrastructure import InfrastructureType


def test_cloudformation_scanner_initialization():
    """Test CloudFormationScanner initialization."""
    scanner = CloudFormationScanner()
    
    assert scanner.get_infrastructure_type() == InfrastructureType.IaC
    supported_patterns = scanner.get_supported_file_patterns()
    assert "*.template" in supported_patterns
    assert "*.json" in supported_patterns
    assert "*.yaml" in supported_patterns
    assert "*.yml" in supported_patterns


def test_cloudformation_scanner_can_handle_file():
    """Test CloudFormationScanner file handling."""
    scanner = CloudFormationScanner()
    
    assert scanner.can_handle_file(Path("template.json")) is True
    assert scanner.can_handle_file(Path("stack.yaml")) is True
    assert scanner.can_handle_file(Path("infrastructure.yml")) is True
    assert scanner.can_handle_file(Path("cloudformation.template")) is True
    assert scanner.can_handle_file(Path("test.txt")) is False
    assert scanner.can_handle_file(Path("main.tf")) is False


def test_cloudformation_scanner_basic_ec2_resource():
    """Test scanning basic EC2 CloudFormation resource."""
    scanner = CloudFormationScanner()
    
    cf_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Basic EC2 instance",
        "Resources": {
            "MyEC2Instance": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": "ami-12345678",
                    "InstanceType": "t2.micro",
                    "Tags": [
                        {
                            "Key": "Name",
                            "Value": "MyInstance"
                        }
                    ]
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(cf_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.type == InfrastructureType.IaC
        assert component.name == "MyEC2Instance"
        assert component.service == "cloudformation"
        assert component.subtype == "AWS::EC2::Instance"
        assert component.configuration["Properties"]["InstanceType"] == "t2.micro"


def test_cloudformation_scanner_yaml_template():
    """Test scanning CloudFormation YAML template."""
    scanner = CloudFormationScanner()
    
    cf_yaml = """
AWSTemplateFormatVersion: '2010-09-09'
Description: 'S3 bucket for storage'
Resources:
  MyS3Bucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: my-test-bucket
      VersioningConfiguration:
        Status: Enabled
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(cf_yaml)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.name == "MyS3Bucket"
        assert component.subtype == "AWS::S3::Bucket"
        assert component.configuration["Properties"]["BucketName"] == "my-test-bucket"


def test_cloudformation_scanner_multiple_resources():
    """Test scanning CloudFormation template with multiple resources."""
    scanner = CloudFormationScanner()
    
    cf_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MyVPC": {
                "Type": "AWS::EC2::VPC",
                "Properties": {
                    "CidrBlock": "10.0.0.0/16"
                }
            },
            "MySubnet": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "VpcId": {"Ref": "MyVPC"},
                    "CidrBlock": "10.0.1.0/24"
                }
            },
            "MySecurityGroup": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "Security group for EC2",
                    "VpcId": {"Ref": "MyVPC"}
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(cf_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 3
        resource_names = [comp.name for comp in components]
        assert "MyVPC" in resource_names
        assert "MySubnet" in resource_names
        assert "MySecurityGroup" in resource_names


def test_cloudformation_scanner_parameters_and_outputs():
    """Test scanning CloudFormation template with parameters and outputs."""
    scanner = CloudFormationScanner()
    
    cf_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Parameters": {
            "InstanceType": {
                "Type": "String",
                "Default": "t2.micro",
                "Description": "EC2 instance type"
            }
        },
        "Resources": {
            "MyInstance": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "InstanceType": {"Ref": "InstanceType"},
                    "ImageId": "ami-12345678"
                }
            }
        },
        "Outputs": {
            "InstanceId": {
                "Description": "Instance ID",
                "Value": {"Ref": "MyInstance"}
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(cf_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should detect parameters, resources, and outputs
        assert len(components) >= 1
        
        # Check that we have the resource
        resource_components = [c for c in components if c.subtype == "AWS::EC2::Instance"]
        assert len(resource_components) == 1
        assert resource_components[0].name == "MyInstance"


def test_cloudformation_scanner_invalid_json():
    """Test scanning invalid JSON CloudFormation file."""
    scanner = CloudFormationScanner()
    
    invalid_json = '{"invalid": json content}'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(invalid_json)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should return empty list for invalid files
        assert components == []


def test_cloudformation_scanner_empty_file():
    """Test scanning empty CloudFormation file."""
    scanner = CloudFormationScanner()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("")
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should return empty list for empty files
        assert components == []


def test_cloudformation_scanner_non_aws_template():
    """Test scanning non-CloudFormation JSON file."""
    scanner = CloudFormationScanner()
    
    non_cf_json = {
        "name": "test",
        "version": "1.0.0",
        "dependencies": {}
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(non_cf_json, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        # Should return empty list for non-CloudFormation files
        assert components == []


def test_cloudformation_scanner_rds_database():
    """Test scanning CloudFormation template with RDS database."""
    scanner = CloudFormationScanner()
    
    cf_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MyDatabase": {
                "Type": "AWS::RDS::DBInstance",
                "Properties": {
                    "DBInstanceClass": "db.t3.micro",
                    "Engine": "mysql",
                    "EngineVersion": "8.0.35",
                    "MasterUsername": "admin",
                    "MasterUserPassword": "mypassword",
                    "AllocatedStorage": "20"
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(cf_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.name == "MyDatabase"
        assert component.subtype == "AWS::RDS::DBInstance"
        assert component.configuration["Properties"]["Engine"] == "mysql"


def test_cloudformation_scanner_lambda_function():
    """Test scanning CloudFormation template with Lambda function."""
    scanner = CloudFormationScanner()
    
    cf_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "MyLambdaFunction": {
                "Type": "AWS::Lambda::Function",
                "Properties": {
                    "FunctionName": "my-function",
                    "Runtime": "python3.9",
                    "Handler": "index.handler",
                    "Code": {
                        "ZipFile": "def handler(event, context): return 'Hello'"
                    }
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(cf_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 1
        component = components[0]
        assert component.name == "MyLambdaFunction"
        assert component.subtype == "AWS::Lambda::Function"
        assert component.configuration["Properties"]["Runtime"] == "python3.9"


def test_cloudformation_scanner_file_not_found():
    """Test scanning non-existent file."""
    scanner = CloudFormationScanner()
    
    components = scanner.scan_file(Path("/non/existent/file.json"))
    
    # Should return empty list for non-existent files
    assert components == []


def test_cloudformation_scanner_complex_template():
    """Test scanning complex CloudFormation template with nested resources."""
    scanner = CloudFormationScanner()
    
    cf_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Complex web application stack",
        "Resources": {
            "ApplicationLoadBalancer": {
                "Type": "AWS::ElasticLoadBalancingV2::LoadBalancer",
                "Properties": {
                    "Type": "application",
                    "Scheme": "internet-facing"
                }
            },
            "AutoScalingGroup": {
                "Type": "AWS::AutoScaling::AutoScalingGroup",
                "Properties": {
                    "MinSize": "1",
                    "MaxSize": "3",
                    "DesiredCapacity": "2"
                }
            },
            "CloudWatchAlarm": {
                "Type": "AWS::CloudWatch::Alarm",
                "Properties": {
                    "AlarmDescription": "High CPU alarm",
                    "MetricName": "CPUUtilization",
                    "Threshold": "80"
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(cf_template, f)
        f.flush()
        
        components = scanner.scan_file(Path(f.name))
        
        assert len(components) == 3
        
        # Verify all resource types are detected
        resource_types = [comp.subtype for comp in components]
        assert "AWS::ElasticLoadBalancingV2::LoadBalancer" in resource_types
        assert "AWS::AutoScaling::AutoScalingGroup" in resource_types
        assert "AWS::CloudWatch::Alarm" in resource_types