"""Test cases for Cloud SDK detector."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from dependency_scanner_tool.infrastructure_scanners.cloud_sdk import CloudSDKDetector
from dependency_scanner_tool.models.infrastructure import InfrastructureType, InfrastructureComponent


class TestCloudSDKDetector:
    """Test cases for CloudSDKDetector."""
    
    def setup_method(self):
        """Set up test environment."""
        self.detector = CloudSDKDetector()
    
    def test_get_supported_file_patterns(self):
        """Test getting supported file patterns."""
        patterns = self.detector.get_supported_file_patterns()
        expected_patterns = [
            "*.py",
            "*.java",
            "*.js",
            "*.ts",
            "*.go",
            "*.rb",
            "*.php",
            "*.cs",
            "requirements.txt",
            "package.json",
            "pom.xml",
            "build.gradle",
            "Gemfile",
            "composer.json",
            "go.mod"
        ]
        assert patterns == expected_patterns
    
    def test_get_infrastructure_type(self):
        """Test getting infrastructure type."""
        assert self.detector.get_infrastructure_type() == InfrastructureType.CLOUD
    
    def test_scan_python_boto3_import(self):
        """Test scanning Python file with boto3 import."""
        python_code = """
import boto3
from boto3.session import Session

def create_s3_client():
    return boto3.client('s3')
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=python_code):
            
            file_path = Path("aws_client.py")
            components = self.detector.scan_file(file_path)
            
            assert len(components) >= 1
            
            # Check for boto3 component
            boto3_component = next((c for c in components if c.name == "boto3"), None)
            assert boto3_component is not None
            assert boto3_component.type == InfrastructureType.CLOUD
            assert boto3_component.service == "aws"
            assert boto3_component.subtype == "sdk"
            assert boto3_component.source_file == str(file_path)
    
    def test_scan_python_azure_sdk_import(self):
        """Test scanning Python file with Azure SDK import."""
        python_code = """
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import azure.functions as func

def create_blob_client():
    return BlobServiceClient(account_url="https://myaccount.blob.core.windows.net")
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=python_code):
            
            file_path = Path("azure_client.py")
            components = self.detector.scan_file(file_path)
            
            assert len(components) >= 1
            
            # Check for Azure SDK components
            azure_components = [c for c in components if c.service == "azure"]
            assert len(azure_components) >= 1
            
            storage_component = next((c for c in azure_components if "storage" in c.name), None)
            assert storage_component is not None
            assert storage_component.type == InfrastructureType.CLOUD
            assert storage_component.subtype == "sdk"
    
    def test_scan_python_gcp_sdk_import(self):
        """Test scanning Python file with GCP SDK import."""
        python_code = """
from google.cloud import storage
from google.cloud import bigquery
from google.auth import default
import google.cloud.functions_v1 as functions

def create_storage_client():
    return storage.Client()
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=python_code):
            
            file_path = Path("gcp_client.py")
            components = self.detector.scan_file(file_path)
            
            assert len(components) >= 1
            
            # Check for GCP SDK components
            gcp_components = [c for c in components if c.service == "gcp"]
            assert len(gcp_components) >= 1
            
            # Check for any Google cloud component
            google_component = next((c for c in gcp_components if "google" in c.name.lower()), None)
            assert google_component is not None
            assert google_component.type == InfrastructureType.CLOUD
            assert google_component.subtype == "sdk"
    
    def test_scan_java_aws_sdk_import(self):
        """Test scanning Java file with AWS SDK import."""
        java_code = """
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.ec2.Ec2Client;
import com.amazonaws.services.dynamodbv2.AmazonDynamoDB;

public class AWSService {
    private S3Client s3Client;
    private Ec2Client ec2Client;
    
    public void initializeClients() {
        s3Client = S3Client.create();
        ec2Client = Ec2Client.create();
    }
}
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=java_code):
            
            file_path = Path("AWSService.java")
            components = self.detector.scan_file(file_path)
            
            assert len(components) >= 1
            
            # Check for AWS SDK components
            aws_components = [c for c in components if c.service == "aws"]
            assert len(aws_components) >= 1
            
            s3_component = next((c for c in aws_components if "s3" in c.name.lower()), None)
            assert s3_component is not None
            assert s3_component.type == InfrastructureType.CLOUD
            assert s3_component.subtype == "sdk"
    
    def test_scan_javascript_aws_sdk_import(self):
        """Test scanning JavaScript file with AWS SDK import."""
        js_code = """
const AWS = require('aws-sdk');
import { S3Client } from '@aws-sdk/client-s3';
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';

const s3 = new AWS.S3();
const s3Client = new S3Client({ region: 'us-east-1' });
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=js_code):
            
            file_path = Path("aws-service.js")
            components = self.detector.scan_file(file_path)
            
            assert len(components) >= 1
            
            # Check for AWS SDK components
            aws_components = [c for c in components if c.service == "aws"]
            assert len(aws_components) >= 1
    
    def test_scan_package_json_aws_sdk(self):
        """Test scanning package.json with AWS SDK dependencies."""
        package_json = """
{
  "name": "my-app",
  "version": "1.0.0",
  "dependencies": {
    "@aws-sdk/client-s3": "^3.0.0",
    "@aws-sdk/client-dynamodb": "^3.0.0",
    "aws-sdk": "^2.1000.0"
  }
}
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=package_json):
            
            file_path = Path("package.json")
            components = self.detector.scan_file(file_path)
            
            assert len(components) >= 1
            
            # Check for AWS SDK components
            aws_components = [c for c in components if c.service == "aws"]
            assert len(aws_components) >= 1
    
    def test_scan_requirements_txt_cloud_sdks(self):
        """Test scanning requirements.txt with cloud SDK dependencies."""
        requirements = """
boto3==1.26.0
botocore==1.29.0
azure-storage-blob==12.0.0
azure-identity==1.12.0
google-cloud-storage==2.7.0
google-cloud-bigquery==3.4.0
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=requirements):
            
            file_path = Path("requirements.txt")
            components = self.detector.scan_file(file_path)
            
            assert len(components) >= 3  # Should detect AWS, Azure, and GCP components
            
            # Check for each cloud provider
            providers = {c.service for c in components}
            assert "aws" in providers
            assert "azure" in providers
            assert "gcp" in providers
    
    def test_scan_pom_xml_aws_sdk(self):
        """Test scanning pom.xml with AWS SDK dependencies."""
        pom_xml = """
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <dependencies>
        <dependency>
            <groupId>software.amazon.awssdk</groupId>
            <artifactId>s3</artifactId>
            <version>2.20.0</version>
        </dependency>
        <dependency>
            <groupId>com.amazonaws</groupId>
            <artifactId>aws-java-sdk-dynamodb</artifactId>
            <version>1.12.0</version>
        </dependency>
    </dependencies>
</project>
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=pom_xml):
            
            file_path = Path("pom.xml")
            components = self.detector.scan_file(file_path)
            
            assert len(components) >= 1
            
            # Check for AWS SDK components
            aws_components = [c for c in components if c.service == "aws"]
            assert len(aws_components) >= 1
    
    def test_scan_no_cloud_sdk_imports(self):
        """Test scanning file with no cloud SDK imports."""
        regular_code = """
import os
import sys
import requests
from datetime import datetime

def fetch_data():
    response = requests.get('https://api.example.com/data')
    return response.json()
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=regular_code):
            
            file_path = Path("regular_code.py")
            components = self.detector.scan_file(file_path)
            
            # Should not detect any cloud SDK components
            assert len(components) == 0
    
    def test_scan_file_not_exists(self):
        """Test scanning file that doesn't exist."""
        file_path = Path("nonexistent.py")
        components = self.detector.scan_file(file_path)
        
        assert len(components) == 0
    
    def test_scan_mixed_cloud_providers(self):
        """Test scanning file with multiple cloud provider SDKs."""
        mixed_code = """
import boto3
from azure.storage.blob import BlobServiceClient
from google.cloud import storage

class MultiCloudService:
    def __init__(self):
        self.aws_s3 = boto3.client('s3')
        self.azure_blob = BlobServiceClient(account_url="https://myaccount.blob.core.windows.net")
        self.gcp_storage = storage.Client()
"""
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=mixed_code):
            
            file_path = Path("multi_cloud.py")
            components = self.detector.scan_file(file_path)
            
            assert len(components) >= 3
            
            # Check for all three cloud providers
            providers = {c.service for c in components}
            assert "aws" in providers
            assert "azure" in providers
            assert "gcp" in providers
    
    def test_scan_unsupported_file_type(self):
        """Test scanning unsupported file type."""
        file_path = Path("document.pdf")
        components = self.detector.scan_file(file_path)
        
        # Should not scan unsupported files
        assert len(components) == 0