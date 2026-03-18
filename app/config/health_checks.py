        # Process results
        services: dict[ServiceType, ServiceHealth] = {}
        for result in results:
            if isinstance(result, ServiceHealth):
                services[result.service] = result
            elif isinstance(result, Exception):
                logger.error(f"Health check task failed: {result}")

        # Add models check (synchronous but wrapped in executor for consistency if needed, 
        # or just run it directly as it's fast)
        services[ServiceType.MODELS] = self.check_models()

        # Determine overall status
        # Only certain services mark the entire system as unhealthy
        critical_services = [ServiceType.DATABASE, ServiceType.REDIS]
        
        overall_status = HealthStatus.HEALTHY
        
        for service_type, health in services.items():
            if health.status == HealthStatus.UNHEALTHY:
                if service_type in critical_services:
                    overall_status = HealthStatus.UNHEALTHY
                    break
                else:
                    overall_status = HealthStatus.DEGRADED
            elif health.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        # Get version
        try:
            from app.__version__ import __version__
            version = __version__
        except ImportError:
            version = "unknown"
