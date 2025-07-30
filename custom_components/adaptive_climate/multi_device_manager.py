"""
Multi-device manager for Adaptive Climate v2.x.

This module provides intelligent device management for areas with multiple
climate devices, automatically determining optimal device roles based on
capabilities and efficiency.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from .mode_mapper import detect_device_capabilities, validate_mode_compatibility

_LOGGER = logging.getLogger(__name__)

class MultiDeviceManager:
    """Manage multiple devices with intelligent role assignment."""
    
    def __init__(self, device_ids: List[str], device_name: str = "Multi-Device"):
        """Initialize multi-device manager."""
        self.device_ids = device_ids
        self.device_name = device_name
        self.device_capabilities = {}
        self.device_efficiency = {}
        self.device_priority = {}
        self.hass = None
        
        _LOGGER.debug(f"[{self.device_name}] Multi-device manager initialized with {len(device_ids)} devices")
    
    def set_hass(self, hass):
        """Set Home Assistant instance."""
        self.hass = hass
    
    def analyze_all_devices(self) -> None:
        """Analyze all devices and their capabilities."""
        _LOGGER.debug(f"[{self.device_name}] Analyzing {len(self.device_ids)} devices...")
        
        for device_id in self.device_ids:
            capabilities = self._detect_device_capabilities(device_id)
            efficiency = self._calculate_device_efficiency(device_id, capabilities)
            priority = self._calculate_device_priority(device_id, capabilities, efficiency)
            
            self.device_capabilities[device_id] = capabilities
            self.device_efficiency[device_id] = efficiency
            self.device_priority[device_id] = priority
            
            _LOGGER.info(f"[{self.device_name}] Device {device_id}: {capabilities}")
    
    def _detect_device_capabilities(self, device_id: str) -> Dict[str, bool]:
        """Detect capabilities for a specific device."""
        if not self.hass:
            _LOGGER.warning(f"[{self.device_name}] Home Assistant not available for device {device_id}")
            return {"is_cool": True, "is_heat": True, "is_fan": True, "is_dry": True}
        
        state = self.hass.states.get(device_id)
        if not state:
            _LOGGER.warning(f"[{self.device_name}] Device {device_id} not available")
            return {"is_cool": True, "is_heat": True, "is_fan": True, "is_dry": True}
        
        supported_hvac_modes = state.attributes.get("hvac_modes", [])
        supported_fan_modes = state.attributes.get("fan_modes", [])
        
        capabilities = detect_device_capabilities(
            supported_hvac_modes, 
            supported_fan_modes, 
            device_id
        )
        
        return capabilities
    
    def _calculate_device_efficiency(self, device_id: str, capabilities: Dict[str, bool]) -> Dict[str, float]:
        """Calculate device efficiency for different operations."""
        # Base efficiency scores (lower = more efficient)
        efficiency = {
            "cool": 1.0,  # Base score
            "heat": 1.0,  # Base score
            "fan": 0.3,   # Very efficient
            "dry": 1.2,   # Less efficient than cool
        }
        
        # Adjust based on device type and capabilities
        device_lower = device_id.lower()
        
        # Detect device type based on capabilities only
        has_cool = capabilities.get("is_cool", False)
        has_heat = capabilities.get("is_heat", False)
        has_fan = capabilities.get("is_fan", False)
        has_dry = capabilities.get("is_dry", False)
        
        # Fan-only devices (apenas ventilação)
        if has_fan and not has_cool and not has_heat and not has_dry:
            efficiency["fan"] = 0.2   # Fan is very efficient
            efficiency["cool"] = 0.5  # Fan can help with cooling
            efficiency["heat"] = float('inf')  # Fan can't heat
            efficiency["dry"] = float('inf')   # Fan can't dehumidify
            _LOGGER.debug(f"[{self.device_name}] Device {device_id} classified as Fan-only (capabilities: {capabilities})")
        
        # AC devices (resfriamento + aquecimento + ventilação)
        elif has_cool and has_heat and has_fan:
            efficiency["cool"] = 0.8  # AC is efficient for cooling
            efficiency["heat"] = 1.5  # AC is less efficient for heating
            efficiency["dry"] = 1.0   # AC is good for dehumidification
            _LOGGER.debug(f"[{self.device_name}] Device {device_id} classified as AC (capabilities: {capabilities})")
        
        # Heat-only devices (apenas aquecimento - TRV, radiadores, aquecedores)
        elif has_heat and not has_cool and not has_dry:
            efficiency["heat"] = 0.7  # Heat-only is very efficient for heating
            efficiency["cool"] = float('inf')  # Can't cool
            efficiency["dry"] = float('inf')   # Can't dehumidify
            efficiency["fan"] = float('inf')   # No fan
            _LOGGER.debug(f"[{self.device_name}] Device {device_id} classified as Heat-only (capabilities: {capabilities})")
        
        # Cool-only devices (apenas resfriamento)
        elif has_cool and not has_heat:
            efficiency["cool"] = 0.8  # AC is efficient for cooling
            efficiency["heat"] = float('inf')  # Can't heat
            efficiency["dry"] = 1.0   # AC is good for dehumidification
            _LOGGER.debug(f"[{self.device_name}] Device {device_id} classified as Cool-only (capabilities: {capabilities})")
        
        # Dry-only devices (apenas desumidificação)
        elif has_dry and not has_cool and not has_heat:
            efficiency["dry"] = 0.9   # Dry is efficient for dehumidification
            efficiency["cool"] = float('inf')  # Can't cool
            efficiency["heat"] = float('inf')  # Can't heat
            efficiency["fan"] = float('inf')   # No fan
            _LOGGER.debug(f"[{self.device_name}] Device {device_id} classified as Dry-only (capabilities: {capabilities})")
        
        # Mixed capabilities (dispositivos com capacidades mistas)
        else:
            # Base efficiency for mixed devices
            if has_cool:
                efficiency["cool"] = 0.8
            if has_heat:
                efficiency["heat"] = 1.0  # Default heat efficiency
            if has_fan:
                efficiency["fan"] = 0.3
            if has_dry:
                efficiency["dry"] = 1.0
            _LOGGER.debug(f"[{self.device_name}] Device {device_id} classified as Mixed capabilities (capabilities: {capabilities})")
        
        # Adjust for capabilities
        for capability in ["cool", "heat", "fan", "dry"]:
            if not capabilities[f"is_{capability}"]:
                efficiency[capability] = float('inf')
        
        return efficiency
    
    def _calculate_device_priority(self, device_id: str, capabilities: Dict[str, bool], efficiency: Dict[str, float]) -> Dict[str, float]:
        """Calculate device priority for different operations."""
        priority = {
            "cool": 0.0,
            "heat": 0.0,
            "fan": 0.0,
            "dry": 0.0,
        }
        
        # Higher priority for more capable and efficient devices
        for capability in ["cool", "heat", "fan", "dry"]:
            if capabilities[f"is_{capability}"] and efficiency[capability] != float('inf'):
                # Lower efficiency score = higher priority
                priority[capability] = 1.0 / efficiency[capability]
        
        return priority
    
    def get_optimal_devices(self, needs: List[str]) -> Dict[str, List[str]]:
        """Get optimal devices for current needs with fallback logic."""
        primary_devices = []
        auxiliary_devices = []
        
        _LOGGER.debug(f"[{self.device_name}] Determining optimal devices for needs: {needs}")
        
        for need in needs:
            available_devices = []
            
            for device_id in self.device_ids:
                if self.device_capabilities[device_id][f"is_{need}"]:
                    priority = self.device_priority[device_id][need]
                    available_devices.append((device_id, priority))
            
            # Sort by priority (highest first)
            available_devices.sort(key=lambda x: x[1], reverse=True)
            
            if available_devices:
                # Check if we have any high-efficiency devices for this need
                high_efficiency_devices = []
                low_efficiency_devices = []
                
                for device_id, priority in available_devices:
                    efficiency = self.device_efficiency[device_id][need]
                    if efficiency < 1.0:  # High efficiency (lower score = more efficient)
                        high_efficiency_devices.append((device_id, priority))
                    else:
                        low_efficiency_devices.append((device_id, priority))
                
                # If we have high-efficiency devices, use them as primary
                if high_efficiency_devices:
                    primary_devices.extend([device_id for device_id, _ in high_efficiency_devices])
                    auxiliary_devices.extend([device_id for device_id, _ in low_efficiency_devices])
                    
                    _LOGGER.debug(f"[{self.device_name}] High-efficiency primary devices for {need}: {[d for d, _ in high_efficiency_devices]}")
                    if low_efficiency_devices:
                        _LOGGER.debug(f"[{self.device_name}] Low-efficiency auxiliary devices for {need}: {[d for d, _ in low_efficiency_devices]}")
                
                # If no high-efficiency devices, use the best available as primary
                else:
                    primary_devices.append(available_devices[0][0])
                    _LOGGER.debug(f"[{self.device_name}] No high-efficiency devices for {need}, using best available as primary: {available_devices[0][0]}")
                    
                    # Remaining devices are auxiliary
                    for device_id, priority in available_devices[1:]:
                        auxiliary_devices.append(device_id)
                        _LOGGER.debug(f"[{self.device_name}] Auxiliary device for {need}: {device_id} (priority: {priority:.2f})")
        
        return {
            "primary": list(set(primary_devices)),  # Remove duplicates
            "auxiliary": list(set(auxiliary_devices))  # Remove duplicates
        }
    
    def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Get comprehensive information about a device."""
        if device_id not in self.device_capabilities:
            return {}
        
        return {
            "capabilities": self.device_capabilities[device_id],
            "efficiency": self.device_efficiency[device_id],
            "priority": self.device_priority[device_id],
        }
    
    def get_all_devices_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all devices."""
        return {device_id: self.get_device_info(device_id) for device_id in self.device_ids}
    
    def validate_device_compatibility(self, device_id: str, requested_hvac: str, requested_fan: str) -> Dict[str, Any]:
        """Validate if a device can handle requested modes."""
        if device_id not in self.device_capabilities:
            return {"compatible": False, "reason": "Device not found"}
        
        capabilities = self.device_capabilities[device_id]
        
        # Get device state for validation
        if not self.hass:
            return {"compatible": False, "reason": "Home Assistant not available"}
        
        state = self.hass.states.get(device_id)
        if not state:
            return {"compatible": False, "reason": "Device not available"}
        
        supported_hvac_modes = state.attributes.get("hvac_modes", [])
        supported_fan_modes = state.attributes.get("fan_modes", [])
        
        validation = validate_mode_compatibility(
            requested_hvac, requested_fan, supported_hvac_modes, supported_fan_modes, device_id
        )
        
        return validation
    
    def is_device_available(self, device_id: str) -> bool:
        """Check if a device is available and operational."""
        if not self.hass:
            return False
        
        state = self.hass.states.get(device_id)
        if not state:
            return False
        
        # Check if device is available and not in error state
        return state.state not in ["unavailable", "unknown", "error"]
    
    def get_available_devices(self, needs: List[str]) -> Dict[str, List[str]]:
        """Get available devices for current needs with fallback logic."""
        primary_devices = []
        auxiliary_devices = []
        
        _LOGGER.debug(f"[{self.device_name}] Getting available devices for needs: {needs}")
        
        for need in needs:
            available_devices = []
            
            for device_id in self.device_ids:
                # Check if device is available and has the required capability
                if (self.is_device_available(device_id) and 
                    self.device_capabilities[device_id][f"is_{need}"]):
                    priority = self.device_priority[device_id][need]
                    available_devices.append((device_id, priority))
            
            # Sort by priority (highest first)
            available_devices.sort(key=lambda x: x[1], reverse=True)
            
            if available_devices:
                # Check if we have any high-efficiency devices for this need
                high_efficiency_devices = []
                low_efficiency_devices = []
                
                for device_id, priority in available_devices:
                    efficiency = self.device_efficiency[device_id][need]
                    if efficiency < 1.0:  # High efficiency (lower score = more efficient)
                        high_efficiency_devices.append((device_id, priority))
                    else:
                        low_efficiency_devices.append((device_id, priority))
                
                # If we have high-efficiency devices, use them as primary
                if high_efficiency_devices:
                    primary_devices.extend([device_id for device_id, _ in high_efficiency_devices])
                    auxiliary_devices.extend([device_id for device_id, _ in low_efficiency_devices])
                    
                    _LOGGER.debug(f"[{self.device_name}] Available high-efficiency primary devices for {need}: {[d for d, _ in high_efficiency_devices]}")
                    if low_efficiency_devices:
                        _LOGGER.debug(f"[{self.device_name}] Available low-efficiency auxiliary devices for {need}: {[d for d, _ in low_efficiency_devices]}")
                
                # If no high-efficiency devices, use the best available as primary (fallback)
                else:
                    primary_devices.append(available_devices[0][0])
                    _LOGGER.debug(f"[{self.device_name}] No high-efficiency devices available for {need}, using best available as primary: {available_devices[0][0]}")
                    
                    # Remaining devices are auxiliary
                    for device_id, priority in available_devices[1:]:
                        auxiliary_devices.append(device_id)
                        _LOGGER.debug(f"[{self.device_name}] Available auxiliary device for {need}: {device_id} (priority: {priority:.2f})")
        
        return {
            "primary": list(set(primary_devices)),  # Remove duplicates
            "auxiliary": list(set(auxiliary_devices))  # Remove duplicates
        } 